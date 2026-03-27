"""Analytics business logic layer."""

from __future__ import annotations

from datetime import date, timedelta

from datapulse.analytics.models import (
    AnalyticsFilter,
    DateRange,
    KPISummary,
    RankingResult,
    ReturnAnalysis,
    TrendResult,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


class AnalyticsService:
    """Orchestrates analytics queries with sensible defaults."""

    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    @staticmethod
    def _default_filter(
        filters: AnalyticsFilter | None = None,
    ) -> AnalyticsFilter:
        """Return filters with a default 30-day date range if none provided."""
        if filters is not None:
            return filters
        today = date.today()
        return AnalyticsFilter(
            date_range=DateRange(
                start_date=today - timedelta(days=30),
                end_date=today,
            )
        )

    def get_dashboard_summary(
        self, target_date: date | None = None
    ) -> KPISummary:
        """KPI cards for dashboard header."""
        target = target_date or date.today()
        log.info("dashboard_summary", target_date=str(target))
        return self._repo.get_kpi_summary(target)

    def get_revenue_trends(
        self, filters: AnalyticsFilter | None = None
    ) -> dict[str, TrendResult]:
        """Daily and monthly revenue trends."""
        f = self._default_filter(filters)
        log.info("revenue_trends", filters=f.model_dump())
        return {
            "daily": self._repo.get_daily_trend(f),
            "monthly": self._repo.get_monthly_trend(f),
        }

    def get_product_insights(
        self, filters: AnalyticsFilter | None = None
    ) -> RankingResult:
        """Top products by net revenue."""
        f = self._default_filter(filters)
        log.info("product_insights", filters=f.model_dump())
        return self._repo.get_top_products(f)

    def get_customer_insights(
        self, filters: AnalyticsFilter | None = None
    ) -> RankingResult:
        """Top customers by net revenue."""
        f = self._default_filter(filters)
        log.info("customer_insights", filters=f.model_dump())
        return self._repo.get_top_customers(f)

    def get_site_comparison(
        self, filters: AnalyticsFilter | None = None
    ) -> RankingResult:
        """Site ranking by net revenue."""
        f = self._default_filter(filters)
        log.info("site_comparison", filters=f.model_dump())
        return self._repo.get_site_performance(f)

    def get_staff_leaderboard(
        self, filters: AnalyticsFilter | None = None
    ) -> RankingResult:
        """Staff ranking by net revenue."""
        f = self._default_filter(filters)
        log.info("staff_leaderboard", filters=f.model_dump())
        return self._repo.get_top_staff(f)

    def get_return_report(
        self, filters: AnalyticsFilter | None = None
    ) -> list[ReturnAnalysis]:
        """Top returns by amount."""
        f = self._default_filter(filters)
        log.info("return_report", filters=f.model_dump())
        return self._repo.get_return_analysis(f)
