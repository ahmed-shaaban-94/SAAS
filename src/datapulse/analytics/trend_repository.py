"""Time-series trend query methods for the analytics layer."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    TrendResult,
)
from datapulse.analytics.queries import (
    SITE_DATE_ONLY,
    build_trend,
    build_where,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class TrendRepository:
    """Time-series trend query methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_daily_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by day."""
        log.info("get_daily_trend", filters=filters.model_dump())
        where, params = build_where(
            filters, date_column="date_key", supported_fields=SITE_DATE_ONLY
        )

        stmt = text(f"""
            SELECT date_key AS period,
                   SUM(total_sales) AS value
            FROM public_marts.agg_sales_daily
            WHERE {where}
            GROUP BY date_key
            ORDER BY date_key
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_trend(list(rows))

    def get_monthly_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by year-month."""
        log.info("get_monthly_trend", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True, supported_fields=SITE_DATE_ONLY)

        stmt = text(f"""
            SELECT LPAD(year::text, 4, '0') || '-'
                   || LPAD(month::text, 2, '0') AS period,
                   SUM(total_sales) AS value
            FROM public_marts.agg_sales_monthly
            WHERE {where}
            GROUP BY year, month
            ORDER BY year, month
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_trend(list(rows))
