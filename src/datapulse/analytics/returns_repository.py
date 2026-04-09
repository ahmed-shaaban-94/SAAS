"""Return analysis and staff quota query methods for the analytics layer."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    ReturnAnalysis,
)
from datapulse.analytics.queries import (
    build_where,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class ReturnsRepository:
    """Return analysis and staff quota query methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_return_analysis(self, filters: AnalyticsFilter) -> list[ReturnAnalysis]:
        """Return top return/credit-note entries."""
        log.info("get_return_analysis", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT a.drug_name, a.drug_brand, a.customer_name,
                   a.return_quantity, a.return_amount,
                   a.return_count,
                   COALESCE(p.origin, 'Other') AS origin
            FROM public_marts.agg_returns a
            LEFT JOIN public_marts.dim_product p
                ON a.product_key = p.product_key AND a.tenant_id = p.tenant_id
            WHERE {where}
              AND a.customer_key != -1
            ORDER BY a.return_amount DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()

        if not rows:
            log.info("return_analysis_empty")
            return []

        return [
            ReturnAnalysis(
                drug_name=str(r[0]),
                drug_brand=str(r[1]),
                customer_name=str(r[2]),
                return_quantity=Decimal(str(r[3])),
                return_amount=Decimal(str(r[4])),
                return_count=int(r[5]),
                origin=str(r[6]),
            )
            for r in rows
        ]

    def get_staff_quota(
        self,
        year: int | None = None,
        month: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch staff quota attainment from feat_staff_quota."""
        conditions = []
        params: dict = {"limit": limit}

        if year is not None:
            conditions.append("year = :year")
            params["year"] = year
        if month is not None:
            conditions.append("month = :month")
            params["month"] = month

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        stmt = text(f"""
            SELECT staff_key, staff_name, staff_position, year, month,
                   actual_revenue, actual_quantity AS actual_transactions,
                   target_revenue, target_transactions,
                   revenue_achievement_pct, transactions_achievement_pct,
                   revenue_variance
            FROM public_marts.feat_staff_quota
            {where}
            ORDER BY actual_revenue DESC
            LIMIT :limit
        """)  # noqa: S608
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]
