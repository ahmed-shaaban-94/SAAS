"""Repository for targets and alerts — raw SQL via SQLAlchemy text().

All queries use parameterized placeholders to prevent SQL injection.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.targets.models import (
    AlertConfigCreate,
    AlertConfigResponse,
    AlertLogResponse,
    BudgetOriginSummary,
    BudgetSummary,
    BudgetVsActualItem,
    QuarterlySummary,
    QuarterlyTargetVsActual,
    TargetCreate,
    TargetResponse,
    TargetSummary,
    TargetVsActual,
)

log = get_logger(__name__)

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


class TargetsRepository:
    """Data-access layer for sales targets and alert configurations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------

    def create_target(self, data: TargetCreate) -> TargetResponse:
        """Insert a new sales target and return the created row."""
        log.info(
            "create_target",
            target_type=data.target_type,
            granularity=data.granularity,
            period=data.period,
        )
        stmt = text("""
            INSERT INTO public.sales_targets
                (target_type, granularity, period, target_value,
                 entity_type, entity_key, created_at, updated_at)
            VALUES
                (:target_type, :granularity, :period, :target_value,
                 :entity_type, :entity_key, NOW(), NOW())
            RETURNING id, target_type, granularity, period, target_value,
                      entity_type, entity_key, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "target_type": data.target_type,
                    "granularity": data.granularity,
                    "period": data.period,
                    "target_value": data.target_value,
                    "entity_type": data.entity_type,
                    "entity_key": data.entity_key,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        return TargetResponse(**row)

    def list_targets(
        self,
        target_type: str | None = None,
        granularity: str | None = None,
        period_prefix: str | None = None,
    ) -> list[TargetResponse]:
        """List targets with optional filters."""
        log.info(
            "list_targets",
            target_type=target_type,
            granularity=granularity,
            period_prefix=period_prefix,
        )
        stmt = text("""
            SELECT id, target_type, granularity, period, target_value,
                   entity_type, entity_key, created_at, updated_at
            FROM public.sales_targets
            WHERE (:target_type IS NULL OR target_type = :target_type)
              AND (:granularity IS NULL OR granularity = :granularity)
              AND (:period_prefix IS NULL OR period LIKE :period_prefix || '%')
            ORDER BY period
        """)
        rows = (
            self._session.execute(
                stmt,
                {
                    "target_type": target_type,
                    "granularity": granularity,
                    "period_prefix": period_prefix,
                },
            )
            .mappings()
            .fetchall()
        )
        return [TargetResponse(**r) for r in rows]

    def delete_target(self, target_id: int) -> bool:
        """Delete a target by ID. Returns True if a row was deleted."""
        log.info("delete_target", target_id=target_id)
        stmt = text("DELETE FROM public.sales_targets WHERE id = :target_id")
        result = self._session.execute(stmt, {"target_id": target_id})
        return result.rowcount > 0  # type: ignore[attr-defined]

    def get_target_vs_actual(self, year: int) -> TargetSummary:
        """Compare monthly revenue targets against actuals for a given year.

        Uses LEFT JOIN between sales_targets and agg_sales_monthly so months
        without targets still show actual values.
        """
        log.info("get_target_vs_actual", year=year)
        year_prefix = str(year)

        stmt = text("""
            WITH monthly_actuals AS (
                SELECT year || '-' || LPAD(month::TEXT, 2, '0') AS period,
                       SUM(total_sales) AS actual_value
                FROM public_marts.agg_sales_monthly
                WHERE year = :year
                GROUP BY year, month
            )
            SELECT t.period,
                   t.target_value,
                   COALESCE(a.actual_value, 0) AS actual_value
            FROM public.sales_targets t
            LEFT JOIN monthly_actuals a ON t.period = a.period
            WHERE t.target_type = 'revenue'
              AND t.granularity = 'monthly'
              AND t.entity_type IS NULL
              AND t.period LIKE :year_prefix || '%'
            ORDER BY t.period
        """)
        rows = self._session.execute(stmt, {"year": year, "year_prefix": year_prefix}).fetchall()

        monthly: list[TargetVsActual] = []
        ytd_target = _ZERO
        ytd_actual = _ZERO

        for r in rows:
            target_val = Decimal(str(r[1]))
            actual_val = Decimal(str(r[2]))
            variance = actual_val - target_val
            achievement = (
                (actual_val / target_val * _HUNDRED).quantize(Decimal("0.01"))
                if target_val != _ZERO
                else _ZERO
            )

            monthly.append(
                TargetVsActual(
                    period=str(r[0]),
                    target_value=target_val,
                    actual_value=actual_val,
                    variance=variance,
                    achievement_pct=achievement,
                )
            )
            ytd_target += target_val
            ytd_actual += actual_val

        ytd_achievement = (
            (ytd_actual / ytd_target * _HUNDRED).quantize(Decimal("0.01"))
            if ytd_target != _ZERO
            else _ZERO
        )

        return TargetSummary(
            monthly_targets=monthly,
            ytd_target=ytd_target,
            ytd_actual=ytd_actual,
            ytd_achievement_pct=ytd_achievement,
        )

    def get_quarterly_summary(self, year: int) -> QuarterlySummary:
        """Aggregate monthly targets vs actuals into quarterly buckets."""

        summary = self.get_target_vs_actual(year)

        quarter_data: dict[int, dict] = {}
        for m in summary.monthly_targets:
            month = int(m.period.split("-")[1])
            q = (month - 1) // 3 + 1
            if q not in quarter_data:
                quarter_data[q] = {"target": _ZERO, "actual": _ZERO}
            quarter_data[q]["target"] += m.target_value
            quarter_data[q]["actual"] += m.actual_value

        quarters = []
        for q in sorted(quarter_data):
            t = quarter_data[q]["target"]
            a = quarter_data[q]["actual"]
            v = a - t
            pct = (a / t * _HUNDRED).quantize(Decimal("0.01")) if t != _ZERO else _ZERO
            quarters.append(
                QuarterlyTargetVsActual(
                    quarter=q,
                    quarter_label=f"Q{q} {year}",
                    target_value=t,
                    actual_value=a,
                    variance=v,
                    achievement_pct=pct,
                )
            )

        return QuarterlySummary(
            quarters=quarters,
            ytd_target=summary.ytd_target,
            ytd_actual=summary.ytd_actual,
            ytd_achievement_pct=summary.ytd_achievement_pct,
        )

    # ------------------------------------------------------------------
    # Budget (from seed_budget_2025)
    # ------------------------------------------------------------------

    _MONTH_NAMES = [
        "",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    def get_budget_vs_actual(self, year: int) -> BudgetSummary:
        """Compare budget from seed_budget_2025 against actual sales by origin."""
        log.info("get_budget_vs_actual", year=year)

        stmt = text("""
            WITH budget AS (
                SELECT month, origin, SUM(budget) AS budget
                FROM public_marts.seed_budget_2025
                WHERE year = :year
                GROUP BY month, origin
            ),
            actuals AS (
                SELECT month, origin, SUM(total_sales) AS actual
                FROM public_marts.agg_sales_by_product
                WHERE year = :year
                  AND origin IS NOT NULL
                GROUP BY month, origin
            )
            SELECT COALESCE(b.month, a.month) AS month,
                   COALESCE(b.origin, a.origin) AS origin,
                   COALESCE(b.budget, 0) AS budget,
                   COALESCE(a.actual, 0) AS actual
            FROM budget b
            FULL OUTER JOIN actuals a
              ON b.month = a.month AND b.origin = a.origin
            ORDER BY month, origin
        """)
        rows = self._session.execute(stmt, {"year": year}).fetchall()

        monthly: list[BudgetVsActualItem] = []
        origin_totals: dict[str, dict[str, Decimal]] = {}
        ytd_budget = _ZERO
        ytd_actual = _ZERO

        for r in rows:
            month_num = int(r[0])
            origin = str(r[1])
            budget_val = Decimal(str(r[2]))
            actual_val = Decimal(str(r[3]))
            variance = actual_val - budget_val
            achievement = (
                (actual_val / budget_val * _HUNDRED).quantize(Decimal("0.01"))
                if budget_val != _ZERO
                else _ZERO
            )

            monthly.append(
                BudgetVsActualItem(
                    month=month_num,
                    month_name=self._MONTH_NAMES[month_num] if month_num <= 12 else str(month_num),
                    origin=origin,
                    budget=budget_val,
                    actual=actual_val,
                    variance=variance,
                    achievement_pct=achievement,
                )
            )

            if origin not in origin_totals:
                origin_totals[origin] = {"budget": _ZERO, "actual": _ZERO}
            origin_totals[origin]["budget"] += budget_val
            origin_totals[origin]["actual"] += actual_val
            ytd_budget += budget_val
            ytd_actual += actual_val

        by_origin: list[BudgetOriginSummary] = []
        for origin, totals in sorted(origin_totals.items()):
            ob = totals["budget"]
            oa = totals["actual"]
            by_origin.append(
                BudgetOriginSummary(
                    origin=origin,
                    ytd_budget=ob,
                    ytd_actual=oa,
                    ytd_variance=oa - ob,
                    ytd_achievement_pct=(
                        (oa / ob * _HUNDRED).quantize(Decimal("0.01")) if ob != _ZERO else _ZERO
                    ),
                )
            )

        ytd_achievement = (
            (ytd_actual / ytd_budget * _HUNDRED).quantize(Decimal("0.01"))
            if ytd_budget != _ZERO
            else _ZERO
        )

        return BudgetSummary(
            monthly=monthly,
            by_origin=by_origin,
            ytd_budget=ytd_budget,
            ytd_actual=ytd_actual,
            ytd_achievement_pct=ytd_achievement,
        )

    # ------------------------------------------------------------------
    # Alert configs
    # ------------------------------------------------------------------

    def list_alert_configs(self) -> list[AlertConfigResponse]:
        """Return all alert configurations."""
        log.info("list_alert_configs")
        stmt = text("""
            SELECT id, alert_name, metric, condition, threshold,
                   entity_type, entity_key, enabled, notify_channels,
                   created_at
            FROM public.alert_configs
            ORDER BY created_at DESC
        """)
        rows = self._session.execute(stmt).mappings().fetchall()
        return [AlertConfigResponse(**r) for r in rows]

    def create_alert_config(self, data: AlertConfigCreate) -> AlertConfigResponse:
        """Insert a new alert configuration and return it."""
        log.info("create_alert_config", alert_name=data.alert_name, metric=data.metric)
        stmt = text("""
            INSERT INTO public.alert_configs
                (alert_name, metric, condition, threshold,
                 entity_type, entity_key, enabled, notify_channels,
                 created_at)
            VALUES
                (:alert_name, :metric, :condition, :threshold,
                 :entity_type, :entity_key, :enabled, :notify_channels::jsonb,
                 NOW())
            RETURNING id, alert_name, metric, condition, threshold,
                      entity_type, entity_key, enabled, notify_channels,
                      created_at
        """)
        import json

        row = (
            self._session.execute(
                stmt,
                {
                    "alert_name": data.alert_name,
                    "metric": data.metric,
                    "condition": data.condition,
                    "threshold": data.threshold,
                    "entity_type": data.entity_type,
                    "entity_key": data.entity_key,
                    "enabled": data.enabled,
                    "notify_channels": json.dumps(data.notify_channels),
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        return AlertConfigResponse(**row)

    def update_alert_config(self, alert_id: int, enabled: bool) -> AlertConfigResponse | None:
        """Toggle the enabled flag on an alert config. Returns None if not found."""
        log.info("update_alert_config", alert_id=alert_id, enabled=enabled)
        stmt = text("""
            UPDATE public.alert_configs
            SET enabled = :enabled
            WHERE id = :alert_id
            RETURNING id, alert_name, metric, condition, threshold,
                      entity_type, entity_key, enabled, notify_channels,
                      created_at
        """)
        row = (
            self._session.execute(stmt, {"alert_id": alert_id, "enabled": enabled})
            .mappings()
            .fetchone()
        )
        if row is None:
            return None
        return AlertConfigResponse(**row)

    # ------------------------------------------------------------------
    # Alert logs
    # ------------------------------------------------------------------

    def list_alert_logs(
        self, limit: int = 50, unacknowledged_only: bool = False
    ) -> list[AlertLogResponse]:
        """Return recent alert log entries, optionally filtered to unacknowledged."""
        log.info("list_alert_logs", limit=limit, unacknowledged_only=unacknowledged_only)
        stmt = text("""
            SELECT l.id, l.alert_config_id,
                   COALESCE(c.alert_name, 'Unknown Alert') AS alert_name,
                   l.fired_at, l.metric_value, l.threshold_value,
                   l.message, l.acknowledged
            FROM public.alerts_log l
            LEFT JOIN public.alert_configs c ON l.alert_config_id = c.id
            WHERE (:ack_only = FALSE OR l.acknowledged = FALSE)
            ORDER BY l.fired_at DESC
            LIMIT :limit
        """)
        rows = (
            self._session.execute(stmt, {"limit": limit, "ack_only": unacknowledged_only})
            .mappings()
            .fetchall()
        )
        return [AlertLogResponse(**r) for r in rows]

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert log entry as acknowledged. Returns True if updated."""
        log.info("acknowledge_alert", alert_id=alert_id)
        stmt = text("""
            UPDATE public.alerts_log
            SET acknowledged = TRUE
            WHERE id = :alert_id AND acknowledged = FALSE
        """)
        result = self._session.execute(stmt, {"alert_id": alert_id})
        return result.rowcount > 0  # type: ignore[attr-defined]
