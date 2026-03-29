"""Analytics business logic layer."""

from __future__ import annotations

from datetime import date, timedelta

from datapulse.analytics.models import (
    AnalyticsFilter,
    CustomerAnalytics,
    DataDateRange,
    DateRange,
    FilterOptions,
    KPISummary,
    ProductPerformance,
    RankingResult,
    ReturnAnalysis,
    StaffPerformance,
    TrendResult,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


class AnalyticsService:
    """Orchestrates analytics queries with sensible defaults."""

    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    def get_date_range(self) -> DataDateRange:
        """Return the min/max dates of available data."""
        min_date, max_date = self._repo.get_data_date_range()
        if min_date is None or max_date is None:
            today = date.today()
            return DataDateRange(min_date=today - timedelta(days=365), max_date=today)
        return DataDateRange(min_date=min_date, max_date=max_date)

    def _default_filter(
        self,
        filters: AnalyticsFilter | None = None,
    ) -> AnalyticsFilter:
        """Return filters with a default 30-day date range if none provided."""
        if filters is not None:
            return filters
        _, max_date = self._repo.get_data_date_range()
        end = max_date or date.today()
        return AnalyticsFilter(
            date_range=DateRange(
                start_date=end - timedelta(days=30),
                end_date=end,
            )
        )

    def get_dashboard_summary(
        self, target_date: date | None = None
    ) -> KPISummary:
        """KPI cards for dashboard header."""
        if target_date is None:
            _, max_date = self._repo.get_data_date_range()
            target = max_date or date.today()
        else:
            target = target_date
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

    def get_daily_trend(
        self, filters: AnalyticsFilter | None = None
    ) -> TrendResult:
        """Daily revenue trend only (avoids fetching monthly data)."""
        f = self._default_filter(filters)
        log.info("daily_trend", filters=f.model_dump())
        return self._repo.get_daily_trend(f)

    def get_monthly_trend(
        self, filters: AnalyticsFilter | None = None
    ) -> TrendResult:
        """Monthly revenue trend only (avoids fetching daily data)."""
        f = self._default_filter(filters)
        log.info("monthly_trend", filters=f.model_dump())
        return self._repo.get_monthly_trend(f)

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

    def get_filter_options(self) -> FilterOptions:
        """Return available filter values for slicers/dropdowns."""
        log.info("filter_options")
        return self._repo.get_filter_options()

    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        """Detailed performance for a single product."""
        log.info("product_detail", product_key=product_key)
        return self._repo.get_product_detail(product_key)

    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        """Detailed analytics for a single customer."""
        log.info("customer_detail", customer_key=customer_key)
        return self._repo.get_customer_detail(customer_key)

    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        """Detailed performance for a single staff member."""
        log.info("staff_detail", staff_key=staff_key)
        return self._repo.get_staff_detail(staff_key)
