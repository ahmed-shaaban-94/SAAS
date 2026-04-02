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
        assert row is not None  # INSERT RETURNING always returns a row
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
        clauses: list[str] = ["1=1"]
        params: dict[str, str | None] = {}

        if target_type is not None:
            clauses.append("target_type = :target_type")
            params["target_type"] = target_type
        if granularity is not None:
            clauses.append("granularity = :granularity")
            params["granularity"] = granularity
        if period_prefix is not None:
            clauses.append("period LIKE :period_prefix || '%'")
            params["period_prefix"] = period_prefix

        where = " AND ".join(clauses)
        stmt = text(f"""
            SELECT id, target_type, granularity, period, target_value,
                   entity_type, entity_key, created_at, updated_at
            FROM public.sales_targets
            WHERE {where}
            ORDER BY period
        """)
        rows = self._session.execute(stmt, params).mappings().fetchall()
        return [TargetResponse(**r) for r in rows]

    def delete_target(self, target_id: int) -> bool:
        """Delete a target by ID. Returns True if a row was deleted."""
        log.info("delete_target", target_id=target_id)
        stmt = text("DELETE FROM public.sales_targets WHERE id = :target_id")
        result = self._session.execute(stmt, {"target_id": target_id})
        return result.rowcount > 0  # type: ignore[union-attr]

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
                       SUM(total_net_amount) AS actual_value
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
        rows = self._session.execute(
            stmt, {"year": year, "year_prefix": year_prefix}
        ).fetchall()

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
        assert row is not None
        return AlertConfigResponse(**row)

    def update_alert_config(
        self, alert_id: int, enabled: bool
    ) -> AlertConfigResponse | None:
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
        log.info(
            "list_alert_logs", limit=limit, unacknowledged_only=unacknowledged_only
        )
        ack_filter = "AND acknowledged = FALSE" if unacknowledged_only else ""
        stmt = text(f"""
            SELECT id, alert_config_id, alert_name, fired_at,
                   metric_value, threshold_value, message, acknowledged
            FROM public.alert_logs
            WHERE 1=1 {ack_filter}
            ORDER BY fired_at DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"limit": limit}).mappings().fetchall()
        return [AlertLogResponse(**r) for r in rows]

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert log entry as acknowledged. Returns True if updated."""
        log.info("acknowledge_alert", alert_id=alert_id)
        stmt = text("""
            UPDATE public.alert_logs
            SET acknowledged = TRUE
            WHERE id = :alert_id AND acknowledged = FALSE
        """)
        result = self._session.execute(stmt, {"alert_id": alert_id})
        return result.rowcount > 0  # type: ignore[union-attr]
