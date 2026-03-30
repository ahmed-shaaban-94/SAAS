"""Analytics business logic layer with Redis caching."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from datapulse.analytics.models import (
    AnalyticsFilter,
    CustomerAnalytics,
    DashboardData,
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
from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.cache import cache_get, cache_set
from datapulse.config import get_settings
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:analytics"


def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    """Build a deterministic cache key from method name and parameters."""
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{_CACHE_PREFIX}:{method}:{h}"
    return f"{_CACHE_PREFIX}:{method}"


class AnalyticsService:
    """Orchestrates analytics queries with sensible defaults and caching."""

    def __init__(self, repo: AnalyticsRepository, detail_repo: DetailRepository | None = None) -> None:
        self._repo = repo
        self._detail_repo = detail_repo

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

    # ------------------------------------------------------------------
    # Cached methods
    # ------------------------------------------------------------------

    def get_dashboard_summary(
        self, target_date: date | None = None
    ) -> KPISummary:
        """KPI cards for dashboard header (cached 300s)."""
        if target_date is None:
            _, max_date = self._repo.get_data_date_range()
            target = max_date or date.today()
        else:
            target = target_date

        key = _cache_key("summary", {"target_date": str(target)})
        cached = cache_get(key)
        if cached is not None:
            log.debug("cache_hit", key=key)
            return KPISummary(**cached)

        log.info("dashboard_summary", target_date=str(target))
        result = self._repo.get_kpi_summary(target)
        cache_set(key, result.model_dump(), ttl=get_settings().redis_default_ttl)
        return result

    def get_filter_options(self) -> FilterOptions:
        """Return available filter values for slicers/dropdowns (cached 600s)."""
        key = _cache_key("filter_options")
        cached = cache_get(key)
        if cached is not None:
            log.debug("cache_hit", key=key)
            return FilterOptions(**cached)

        log.info("filter_options")
        result = self._repo.get_filter_options()
        cache_set(key, result.model_dump(), ttl=get_settings().redis_dashboard_ttl)
        return result

    def get_dashboard_data(
        self, target_date: date | None = None
    ) -> DashboardData:
        """Composite dashboard payload — KPI + trends + rankings + filters (cached 600s)."""
        if target_date is None:
            _, max_date = self._repo.get_data_date_range()
            target_date = max_date or date.today()
        key = _cache_key("dashboard", {"target_date": str(target_date)})
        cached = cache_get(key)
        if cached is not None:
            log.debug("cache_hit", key=key)
            return DashboardData(**cached)

        log.info("dashboard_data", target_date=str(target_date))
        kpi = self.get_dashboard_summary(target_date)
        default_f = self._default_filter()
        result = DashboardData(
            kpi=kpi,
            daily_trend=self._repo.get_daily_trend(default_f),
            monthly_trend=self._repo.get_monthly_trend(default_f),
            top_products=self._repo.get_top_products(default_f),
            top_customers=self._repo.get_top_customers(default_f),
            top_staff=self._repo.get_top_staff(default_f),
            filter_options=self.get_filter_options(),
        )
        cache_set(key, result.model_dump(), ttl=get_settings().redis_dashboard_ttl)
        return result

    # ------------------------------------------------------------------
    # Non-cached methods (filter-dependent, short-lived)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Detail methods (uncached — low volume, entity-specific)
    # ------------------------------------------------------------------

    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        """Detailed performance for a single product."""
        log.info("product_detail", product_key=product_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_product_detail(product_key)

    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        """Detailed analytics for a single customer."""
        log.info("customer_detail", customer_key=customer_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_customer_detail(customer_key)

    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        """Detailed performance for a single staff member."""
        log.info("staff_detail", staff_key=staff_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_staff_detail(staff_key)
