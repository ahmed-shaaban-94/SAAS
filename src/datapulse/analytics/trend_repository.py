"""Time-series trend query methods for the analytics layer."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

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
    safe_growth,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class TrendRepository:
    """Time-series trend query methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_daily_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by day with period-over-period growth."""
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
        trend = build_trend(list(rows))

        # Inject proper period-over-period growth
        trend = self._inject_period_growth(trend, filters, granularity="daily")
        return trend

    def get_monthly_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by year-month with period-over-period growth."""
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
        trend = build_trend(list(rows))

        # Inject proper period-over-period growth
        trend = self._inject_period_growth(trend, filters, granularity="monthly")
        return trend

    def _inject_period_growth(
        self,
        trend: TrendResult,
        filters: AnalyticsFilter,
        *,
        granularity: str,
    ) -> TrendResult:
        """Replace growth_pct with true period-over-period comparison.

        Computes: growth = (current_period_total - previous_period_total)
                           / previous_period_total * 100

        Where previous_period is the same-length window shifted back.
        """
        if not trend.points or trend.total == _ZERO:
            return trend

        if filters.date_range is None:
            return trend

        start = filters.date_range.start_date
        end = filters.date_range.end_date
        period_days = (end - start).days + 1
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)

        if granularity == "daily":
            prev_total = self._query_daily_total(prev_start, prev_end, filters)
        else:
            prev_total = self._query_monthly_total(prev_start, prev_end, filters)

        growth = safe_growth(trend.total, prev_total) if prev_total is not None else None

        return TrendResult(
            points=trend.points,
            total=trend.total,
            average=trend.average,
            minimum=trend.minimum,
            maximum=trend.maximum,
            growth_pct=growth,
            stats=trend.stats,
        )

    def _query_daily_total(
        self,
        start: date,
        end: date,
        filters: AnalyticsFilter,
    ) -> Decimal | None:
        """Sum agg_sales_daily for a date range, respecting site filter."""
        prev_filters = AnalyticsFilter(
            date_range=type(filters.date_range)(start_date=start, end_date=end)
            if filters.date_range is not None
            else None,
            site_key=filters.site_key,
        )
        where, params = build_where(
            prev_filters, date_column="date_key", supported_fields=SITE_DATE_ONLY
        )
        stmt = text(f"""
            SELECT ROUND(SUM(total_sales), 2) AS total
            FROM public_marts.agg_sales_daily
            WHERE {where}
        """)
        row = self._session.execute(stmt, params).fetchone()
        if row is None or row[0] is None:
            return None
        return Decimal(str(row[0]))

    def _query_monthly_total(
        self,
        start: date,
        end: date,
        filters: AnalyticsFilter,
    ) -> Decimal | None:
        """Sum agg_sales_monthly for a date range, respecting site filter."""
        prev_filters = AnalyticsFilter(
            date_range=type(filters.date_range)(start_date=start, end_date=end)
            if filters.date_range is not None
            else None,
            site_key=filters.site_key,
        )
        where, params = build_where(
            prev_filters, use_year_month=True, supported_fields=SITE_DATE_ONLY
        )
        stmt = text(f"""
            SELECT ROUND(SUM(total_sales), 2) AS total
            FROM public_marts.agg_sales_monthly
            WHERE {where}
        """)
        row = self._session.execute(stmt, params).fetchone()
        if row is None or row[0] is None:
            return None
        return Decimal(str(row[0]))
