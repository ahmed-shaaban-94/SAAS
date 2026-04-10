"""Repository for dbt feature store models.

Surfaces the 5 feature tables that were previously dead (not exposed via API):
- feat_revenue_daily_rolling
- feat_revenue_site_rolling
- feat_seasonality_monthly
- feat_seasonality_daily
- feat_product_lifecycle
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class FeatureStoreRepository:
    """Read-only queries against dbt feature store tables in public_marts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # feat_revenue_daily_rolling
    # ------------------------------------------------------------------

    def get_revenue_daily_rolling(
        self,
        *,
        days: int = 90,
        limit: int = 200,
    ) -> list[dict]:
        """Daily revenue with rolling MAs, volatility, and trend ratios."""
        log.info("get_revenue_daily_rolling", days=days, limit=limit)
        stmt = text("""
            SELECT date_key, full_date, day_of_week, is_weekend,
                   daily_gross_amount, daily_transactions, daily_unique_customers,
                   ma_7d_revenue, ma_30d_revenue, ma_90d_revenue,
                   volatility_30d,
                   trend_ratio_7d_30d, trend_ratio_30d_90d,
                   deviation_from_ma30,
                   same_day_last_week, same_day_last_year
            FROM public_marts.feat_revenue_daily_rolling
            WHERE full_date >= CURRENT_DATE - :days
            ORDER BY full_date DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"days": days, "limit": limit}).mappings().all()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # feat_revenue_site_rolling
    # ------------------------------------------------------------------

    def get_revenue_site_rolling(
        self,
        *,
        site_key: int | None = None,
        days: int = 30,
        limit: int = 200,
    ) -> list[dict]:
        """Per-site daily rolling with cross-site comparison."""
        log.info("get_revenue_site_rolling", site_key=site_key, days=days, limit=limit)

        conditions = ["full_date >= CURRENT_DATE - :days"]
        params: dict = {"days": days, "limit": limit}

        if site_key is not None:
            conditions.append("site_key = :site_key")
            params["site_key"] = site_key

        where = " AND ".join(conditions)

        stmt = text(f"""
            SELECT date_key, site_key, full_date,
                   daily_gross_amount, daily_transactions,
                   site_ma_7d, site_ma_30d, site_sum_30d,
                   site_vs_avg_ratio, site_revenue_share
            FROM public_marts.feat_revenue_site_rolling
            WHERE {where}
            ORDER BY full_date DESC, site_key
            LIMIT :limit
        """)  # noqa: S608
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # feat_seasonality_monthly
    # ------------------------------------------------------------------

    def get_seasonality_monthly(self) -> list[dict]:
        """Monthly seasonal indices (12 rows per tenant)."""
        log.info("get_seasonality_monthly")
        stmt = text("""
            SELECT month, month_name, avg_monthly_revenue, avg_monthly_txn,
                   stddev_monthly_revenue, years_of_data,
                   month_revenue_index, month_txn_index
            FROM public_marts.feat_seasonality_monthly
            ORDER BY month
        """)
        rows = self._session.execute(stmt).mappings().all()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # feat_seasonality_daily
    # ------------------------------------------------------------------

    def get_seasonality_daily(self) -> list[dict]:
        """Day-of-week seasonal indices (7 rows per tenant)."""
        log.info("get_seasonality_daily")
        stmt = text("""
            SELECT day_of_week, day_name, is_weekend,
                   avg_revenue_by_dow, avg_txn_by_dow, avg_customers_by_dow,
                   stddev_revenue_by_dow, sample_count,
                   dow_revenue_index, dow_txn_index
            FROM public_marts.feat_seasonality_daily
            ORDER BY day_of_week
        """)
        rows = self._session.execute(stmt).mappings().all()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # feat_product_lifecycle
    # ------------------------------------------------------------------

    def get_product_lifecycle(
        self,
        *,
        phase: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Product lifecycle classification with optional phase filter."""
        log.info("get_product_lifecycle", phase=phase, limit=limit)

        conditions = []
        params: dict = {"limit": limit}

        if phase is not None:
            conditions.append("lifecycle_phase = :phase")
            params["phase"] = phase

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        stmt = text(f"""
            SELECT product_key, drug_code, drug_name, drug_brand, drug_category,
                   avg_recent_growth, quarters_active,
                   total_lifetime_revenue, total_lifetime_quantity,
                   first_sale_quarter, last_sale_quarter,
                   lifecycle_phase
            FROM public_marts.feat_product_lifecycle
            {where}
            ORDER BY total_lifetime_revenue DESC
            LIMIT :limit
        """)  # noqa: S608
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    def get_lifecycle_distribution(self) -> dict:
        """Count of products per lifecycle phase."""
        log.info("get_lifecycle_distribution")
        stmt = text("""
            SELECT lifecycle_phase, COUNT(*) AS cnt
            FROM public_marts.feat_product_lifecycle
            GROUP BY lifecycle_phase
        """)
        rows = self._session.execute(stmt).fetchall()

        phase_counts: dict[str, int] = {}
        total = 0
        for r in rows:
            phase_counts[str(r[0])] = int(r[1])
            total += int(r[1])

        return {
            "growth": phase_counts.get("Growth", 0),
            "mature": phase_counts.get("Mature", 0),
            "decline": phase_counts.get("Decline", 0),
            "dormant": phase_counts.get("Dormant", 0),
            "total": total,
        }
