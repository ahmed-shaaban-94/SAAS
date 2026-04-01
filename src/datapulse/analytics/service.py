"""Analytics business logic layer with Redis caching."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.comparison_repository import ComparisonRepository
from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.hierarchy_repository import HierarchyRepository
from datapulse.analytics.models import (
    AnalyticsFilter,
    BillingBreakdown,
    CustomerAnalytics,
    CustomerTypeBreakdown,
    DashboardData,
    DataDateRange,
    DateRange,
    FilterOptions,
    KPISummary,
    ProductHierarchy,
    ProductPerformance,
    RankingResult,
    ReturnAnalysis,
    SiteDetail,
    StaffPerformance,
    TopMovers,
    TrendResult,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.cache import cache_get, cache_set
from datapulse.cache_decorator import cached
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

    def __init__(
        self,
        repo: AnalyticsRepository,
        detail_repo: DetailRepository | None = None,
        breakdown_repo: BreakdownRepository | None = None,
        comparison_repo: ComparisonRepository | None = None,
        hierarchy_repo: HierarchyRepository | None = None,
    ) -> None:
        self._repo = repo
        self._detail_repo = detail_repo
        self._breakdown_repo = breakdown_repo
        self._comparison_repo = comparison_repo
        self._hierarchy_repo = hierarchy_repo

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

    def get_dashboard_summary(self, target_date: date | None = None) -> KPISummary:
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

    def get_dashboard_data(self, target_date: date | None = None) -> DashboardData:
        """Composite dashboard payload — KPI + trends + rankings + filters (cached 600s)."""
        _, max_date = self._repo.get_data_date_range()
        if target_date is None:
            target_date = max_date or date.today()
        key = _cache_key("dashboard", {"target_date": str(target_date)})
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return DashboardData(**cached_val)

        log.info("dashboard_data", target_date=str(target_date))
        kpi = self.get_dashboard_summary(target_date)
        end = max_date or date.today()
        default_f = AnalyticsFilter(
            date_range=DateRange(start_date=end - timedelta(days=30), end_date=end)
        )
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
    # Filter-dependent methods (cached 60-120s via @cached decorator)
    # ------------------------------------------------------------------

    @cached(ttl=90, prefix=_CACHE_PREFIX)
    def get_revenue_trends(self, filters: AnalyticsFilter | None = None) -> dict[str, TrendResult]:
        """Daily and monthly revenue trends (cached 90s)."""
        f = self._default_filter(filters)
        log.info("revenue_trends", filters=f.model_dump())
        return {
            "daily": self._repo.get_daily_trend(f),
            "monthly": self._repo.get_monthly_trend(f),
        }

    @cached(ttl=60, prefix=_CACHE_PREFIX)
    def get_daily_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        """Daily revenue trend only (cached 60s)."""
        f = self._default_filter(filters)
        log.info("daily_trend", filters=f.model_dump())
        return self._repo.get_daily_trend(f)

    @cached(ttl=60, prefix=_CACHE_PREFIX)
    def get_monthly_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        """Monthly revenue trend only (cached 60s)."""
        f = self._default_filter(filters)
        log.info("monthly_trend", filters=f.model_dump())
        return self._repo.get_monthly_trend(f)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_product_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Top products by net revenue (cached 120s)."""
        f = self._default_filter(filters)
        log.info("product_insights", filters=f.model_dump())
        return self._repo.get_top_products(f)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_customer_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Top customers by net revenue (cached 120s)."""
        f = self._default_filter(filters)
        log.info("customer_insights", filters=f.model_dump())
        return self._repo.get_top_customers(f)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_site_comparison(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Site ranking by net revenue (cached 120s)."""
        f = self._default_filter(filters)
        log.info("site_comparison", filters=f.model_dump())
        return self._repo.get_site_performance(f)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_staff_leaderboard(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Staff ranking by net revenue (cached 120s)."""
        f = self._default_filter(filters)
        log.info("staff_leaderboard", filters=f.model_dump())
        return self._repo.get_top_staff(f)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_return_report(self, filters: AnalyticsFilter | None = None) -> list[ReturnAnalysis]:
        """Top returns by amount (cached 120s)."""
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

    # ------------------------------------------------------------------
    # Phase 2: Billing & Customer Type
    # ------------------------------------------------------------------

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_billing_breakdown(self, filters: AnalyticsFilter | None = None) -> BillingBreakdown:
        """Billing method distribution (cached 120s)."""
        if self._breakdown_repo is None:
            raise RuntimeError("BreakdownRepository not configured")
        f = self._default_filter(filters)
        log.info("billing_breakdown", filters=f.model_dump())
        return self._breakdown_repo.get_billing_breakdown(f)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_customer_type_breakdown(
        self, filters: AnalyticsFilter | None = None
    ) -> CustomerTypeBreakdown:
        """Walk-in vs insurance vs other distribution by month (cached 120s)."""
        if self._breakdown_repo is None:
            raise RuntimeError("BreakdownRepository not configured")
        f = self._default_filter(filters)
        log.info("customer_type_breakdown", filters=f.model_dump())
        return self._breakdown_repo.get_customer_type_breakdown(f)

    # ------------------------------------------------------------------
    # Phase 3: Comparative Analytics
    # ------------------------------------------------------------------

    def get_top_movers(
        self,
        entity_type: str,
        filters: AnalyticsFilter | None = None,
        limit: int = 5,
    ) -> TopMovers:
        """Top gainers and losers vs previous period."""
        if self._comparison_repo is None:
            raise RuntimeError("ComparisonRepository not configured")

        current_f = self._default_filter(filters)
        log.info("top_movers", entity_type=entity_type, filters=current_f.model_dump())

        # Compute previous period (same duration, shifted back)
        if current_f.date_range is not None:
            dr = current_f.date_range
            duration = dr.end_date - dr.start_date
            prev_end = dr.start_date - timedelta(days=1)
            prev_start = prev_end - duration
            previous_f = AnalyticsFilter(
                date_range=DateRange(start_date=prev_start, end_date=prev_end),
                site_key=current_f.site_key,
                category=current_f.category,
                brand=current_f.brand,
                staff_key=current_f.staff_key,
                limit=current_f.limit,
            )
        else:
            # No date range — use last 30d vs prior 30d
            _, max_date = self._repo.get_data_date_range()
            end = max_date or date.today()
            current_f = AnalyticsFilter(
                date_range=DateRange(start_date=end - timedelta(days=30), end_date=end)
            )
            previous_f = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=61),
                    end_date=end - timedelta(days=31),
                )
            )

        return self._comparison_repo.get_top_movers(entity_type, current_f, previous_f, limit)

    # ------------------------------------------------------------------
    # Phase 4: Site Detail & Product Hierarchy
    # ------------------------------------------------------------------

    def get_site_detail(self, site_key: int) -> SiteDetail | None:
        """Detailed metrics for a single site."""
        log.info("site_detail", site_key=site_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_site_detail(site_key)

    @cached(ttl=120, prefix=_CACHE_PREFIX)
    def get_product_hierarchy(self, filters: AnalyticsFilter | None = None) -> ProductHierarchy:
        """Category > Brand > Product hierarchy view (cached 120s)."""
        if self._hierarchy_repo is None:
            raise RuntimeError("HierarchyRepository not configured")
        f = self._default_filter(filters)
        log.info("product_hierarchy", filters=f.model_dump())
        return self._hierarchy_repo.get_product_hierarchy(f)
