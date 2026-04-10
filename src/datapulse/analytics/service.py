"""Analytics business logic layer with Redis caching."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from datapulse.analytics.advanced_repository import AdvancedRepository
from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.comparison_repository import ComparisonRepository
from datapulse.analytics.customer_health import CustomerHealthRepository
from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.diagnostics import DiagnosticsRepository
from datapulse.analytics.feature_store_repository import FeatureStoreRepository
from datapulse.analytics.hierarchy_repository import HierarchyRepository
from datapulse.analytics.models import (
    ABCAnalysis,
    AnalyticsFilter,
    BillingBreakdown,
    CustomerAnalytics,
    CustomerHealthScore,
    CustomerTypeBreakdown,
    DashboardData,
    DataDateRange,
    DateRange,
    FilterOptions,
    HealthDistribution,
    HeatmapData,
    KPISummary,
    LifecycleDistribution,
    ProductHierarchy,
    ProductLifecycle,
    ProductPerformance,
    RankingResult,
    ReturnAnalysis,
    ReturnsTrend,
    RevenueDailyRolling,
    RevenueSiteRolling,
    SeasonalityDaily,
    SeasonalityMonthly,
    SegmentSummary,
    SiteDetail,
    StaffPerformance,
    TopMovers,
    TrendResult,
    WaterfallAnalysis,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.cache import cache_get, cache_set, current_tenant_id, get_cache_version
from datapulse.cache_decorator import cached
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:analytics"


def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    """Build a deterministic, versioned, tenant-scoped cache key.

    Key format: dp:v{run_id}:t{tenant}:{method}:{args_hash}
    Bumping the pipeline run_id version orphans all prior keys; they
    expire naturally via TTL — no O(N) SCAN invalidation needed.
    """
    tid = current_tenant_id.get("")
    tenant_segment = f"t{tid}" if tid else "t0"
    version = get_cache_version()
    prefix = f"dp:{version}:{tenant_segment}"
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{prefix}:{method}:{h}"
    return f"{prefix}:{method}"


class AnalyticsService:
    """Orchestrates analytics queries with sensible defaults and caching."""

    def __init__(
        self,
        repo: AnalyticsRepository,
        detail_repo: DetailRepository | None = None,
        breakdown_repo: BreakdownRepository | None = None,
        comparison_repo: ComparisonRepository | None = None,
        hierarchy_repo: HierarchyRepository | None = None,
        advanced_repo: AdvancedRepository | None = None,
        diagnostics_repo: DiagnosticsRepository | None = None,
        customer_health_repo: CustomerHealthRepository | None = None,
        feature_store_repo: FeatureStoreRepository | None = None,
    ) -> None:
        self._repo = repo
        self._detail_repo = detail_repo
        self._breakdown_repo = breakdown_repo
        self._comparison_repo = comparison_repo
        self._hierarchy_repo = hierarchy_repo
        self._advanced_repo = advanced_repo
        self._diagnostics_repo = diagnostics_repo
        self._customer_health_repo = customer_health_repo
        self._feature_store_repo = feature_store_repo

    def get_date_range(self) -> DataDateRange:
        """Return the min/max dates of available data (cached 3600s)."""
        key = _cache_key("date_range")
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return DataDateRange(**cached_val)

        min_date, max_date = self._repo.get_data_date_range()
        if min_date is None or max_date is None:
            today = date.today()
            return DataDateRange(min_date=today - timedelta(days=365), max_date=today)
        result = DataDateRange(min_date=min_date, max_date=max_date)
        cache_set(key, result.model_dump(mode="json"), ttl=3600)
        return result

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
        """KPI cards for dashboard header (cached 600s)."""
        if target_date is None:
            _, max_date = self._repo.get_data_date_range()
            target = max_date or date.today()
        else:
            target = target_date

        key = _cache_key("summary", {"target_date": str(target)})
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return KPISummary(**cached_val)

        log.info("dashboard_summary", target_date=str(target))
        result = self._repo.get_kpi_summary(target)
        cache_set(key, result.model_dump(mode="json"), ttl=600)
        return result

    def get_filter_options(self) -> FilterOptions:
        """Return available filter values for slicers/dropdowns (cached 3600s)."""
        key = _cache_key("filter_options")
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return FilterOptions(**cached_val)

        log.info("filter_options")
        result = self._repo.get_filter_options()
        cache_set(key, result.model_dump(mode="json"), ttl=3600)
        return result

    def get_dashboard_data(
        self,
        target_date: date | None = None,
        filters: AnalyticsFilter | None = None,
    ) -> DashboardData:
        """Composite dashboard payload — KPI + trends + rankings + filters (cached 600s).

        Accepts a full ``AnalyticsFilter`` with optional dimensional filters
        (site_key, category, brand, staff_key).  Falls back to a 30-day window
        from the latest data date when no filters are given.
        """
        _, max_date = self._repo.get_data_date_range()
        end = max_date or date.today()

        if filters is None:
            if target_date is None:
                target_date = end
            filters = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=30),
                    end_date=end,
                )
            )
        elif filters.date_range is None:
            filters = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=30),
                    end_date=end,
                ),
                site_key=filters.site_key,
                category=filters.category,
                brand=filters.brand,
                staff_key=filters.staff_key,
                limit=filters.limit,
            )

        key = _cache_key(
            "dashboard",
            filters.model_dump(exclude_none=True),
        )
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return DashboardData(**cached_val)

        log.info("dashboard_data", filters=filters.model_dump())

        # KPI: aggregate over the entire range
        kpi = self._repo.get_kpi_summary_range(filters)

        result = DashboardData(
            kpi=kpi,
            daily_trend=self._repo.get_daily_trend(filters),
            monthly_trend=self._repo.get_monthly_trend(filters),
            top_products=self._repo.get_top_products(filters),
            top_customers=self._repo.get_top_customers(filters),
            top_staff=self._repo.get_top_staff(filters),
            filter_options=self.get_filter_options(),
        )
        cache_set(key, result.model_dump(mode="json"), ttl=600)
        return result

    # ------------------------------------------------------------------
    # Filter-dependent methods (cached via @cached decorator)
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

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_daily_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        """Daily revenue trend only (cached 300s)."""
        f = self._default_filter(filters)
        log.info("daily_trend", filters=f.model_dump())
        return self._repo.get_daily_trend(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_monthly_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        """Monthly revenue trend only (cached 300s)."""
        f = self._default_filter(filters)
        log.info("monthly_trend", filters=f.model_dump())
        return self._repo.get_monthly_trend(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Top products by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("product_insights", filters=f.model_dump())
        return self._repo.get_top_products(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Top customers by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("customer_insights", filters=f.model_dump())
        return self._repo.get_top_customers(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_site_comparison(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Site ranking by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("site_comparison", filters=f.model_dump())
        return self._repo.get_site_performance(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_staff_leaderboard(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Staff ranking by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("staff_leaderboard", filters=f.model_dump())
        return self._repo.get_top_staff(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_origin_breakdown(self, filters: AnalyticsFilter | None = None) -> list[dict]:
        """Revenue breakdown by product origin (cached 300s)."""
        f = self._default_filter(filters)
        return self._repo.get_origin_breakdown(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_return_report(self, filters: AnalyticsFilter | None = None) -> list[ReturnAnalysis]:
        """Top returns by amount (cached 300s)."""
        f = self._default_filter(filters)
        log.info("return_report", filters=f.model_dump())
        return self._repo.get_return_analysis(f)

    # ------------------------------------------------------------------
    # Detail methods (cached 300s — entity-specific)
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        """Detailed performance for a single product (cached 300s)."""
        log.info("product_detail", product_key=product_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_product_detail(product_key)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        """Detailed analytics for a single customer (cached 300s)."""
        log.info("customer_detail", customer_key=customer_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_customer_detail(customer_key)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        """Detailed performance for a single staff member (cached 300s)."""
        log.info("staff_detail", staff_key=staff_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_staff_detail(staff_key)

    # ------------------------------------------------------------------
    # Phase 2: Billing & Customer Type
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_billing_breakdown(self, filters: AnalyticsFilter | None = None) -> BillingBreakdown:
        """Billing method distribution (cached 300s)."""
        if self._breakdown_repo is None:
            raise RuntimeError("BreakdownRepository not configured")
        f = self._default_filter(filters)
        log.info("billing_breakdown", filters=f.model_dump())
        return self._breakdown_repo.get_billing_breakdown(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_type_breakdown(
        self, filters: AnalyticsFilter | None = None
    ) -> CustomerTypeBreakdown:
        """Walk-in vs insurance vs other distribution by month (cached 300s)."""
        if self._breakdown_repo is None:
            raise RuntimeError("BreakdownRepository not configured")
        f = self._default_filter(filters)
        log.info("customer_type_breakdown", filters=f.model_dump())
        return self._breakdown_repo.get_customer_type_breakdown(f)

    # ------------------------------------------------------------------
    # Phase 3: Comparative Analytics
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_top_movers(
        self,
        entity_type: str,
        filters: AnalyticsFilter | None = None,
        limit: int = 5,
    ) -> TopMovers:
        """Top gainers and losers vs previous period (cached 300s)."""
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

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_site_detail(self, site_key: int) -> SiteDetail | None:
        """Detailed metrics for a single site."""
        log.info("site_detail", site_key=site_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_site_detail(site_key)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_hierarchy(self, filters: AnalyticsFilter | None = None) -> ProductHierarchy:
        """Category > Brand > Product hierarchy view (cached 300s)."""
        if self._hierarchy_repo is None:
            raise RuntimeError("HierarchyRepository not configured")
        f = self._default_filter(filters)
        log.info("product_hierarchy", filters=f.model_dump())
        return self._hierarchy_repo.get_product_hierarchy(f)

    # ------------------------------------------------------------------
    # Phase 5: CEO Review — Advanced Analytics
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_abc_analysis(
        self, entity: str = "product", filters: AnalyticsFilter | None = None
    ) -> ABCAnalysis:
        """ABC/Pareto analysis for products or customers (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        f = self._default_filter(filters)
        return self._advanced_repo.get_abc_analysis(f, entity)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_heatmap(self, year: int) -> HeatmapData:
        """Calendar heatmap — daily revenue for a year (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        return self._advanced_repo.get_heatmap_data(year)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_returns_trend(self, filters: AnalyticsFilter | None = None) -> ReturnsTrend:
        """Monthly returns trend (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        f = self._default_filter(filters)
        return self._advanced_repo.get_returns_trend(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_segment_summary(self) -> list[SegmentSummary]:
        """Customer RFM segment summary (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        return self._advanced_repo.get_segment_summary()

    # ------------------------------------------------------------------
    # Enhancement 4: Why Engine — Revenue Decomposition
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_why_changed(
        self,
        filters: AnalyticsFilter | None = None,
        limit: int = 15,
    ) -> WaterfallAnalysis:
        """Decompose revenue change into dimension-level drivers (cached 300s)."""
        if self._diagnostics_repo is None:
            raise RuntimeError("DiagnosticsRepository not configured")

        current_f = self._default_filter(filters)
        log.info("why_changed", filters=current_f.model_dump())

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

        return self._diagnostics_repo.get_revenue_drivers(current_f, previous_f, limit=limit)

    # ------------------------------------------------------------------
    # Enhancement 4: Customer Health Score
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_health(
        self,
        band: str | None = None,
        limit: int = 50,
    ) -> list[CustomerHealthScore]:
        """Customer health scores, optionally filtered by band (cached 300s)."""
        if self._customer_health_repo is None:
            raise RuntimeError("CustomerHealthRepository not configured")
        return self._customer_health_repo.get_health_scores(band=band, limit=limit)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_health_distribution(self) -> HealthDistribution:
        """Distribution of customers across health bands (cached 300s)."""
        if self._customer_health_repo is None:
            raise RuntimeError("CustomerHealthRepository not configured")
        return self._customer_health_repo.get_health_distribution()

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_at_risk_customers(self, limit: int = 20) -> list[CustomerHealthScore]:
        """At-risk and critical customers, lowest score first (cached 300s)."""
        if self._customer_health_repo is None:
            raise RuntimeError("CustomerHealthRepository not configured")
        return self._customer_health_repo.get_at_risk_customers(limit=limit)

    # ------------------------------------------------------------------
    # Feature Store: Revenue Rolling, Seasonality, Product Lifecycle
    # ------------------------------------------------------------------

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_revenue_daily_rolling(
        self,
        days: int = 90,
        limit: int = 200,
    ) -> list[RevenueDailyRolling]:
        """Daily revenue with rolling MAs and trend ratios (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_revenue_daily_rolling(days=days, limit=limit)
        return [RevenueDailyRolling(**r) for r in rows]

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_revenue_site_rolling(
        self,
        site_key: int | None = None,
        days: int = 30,
        limit: int = 200,
    ) -> list[RevenueSiteRolling]:
        """Per-site rolling with cross-site comparison (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_revenue_site_rolling(
            site_key=site_key,
            days=days,
            limit=limit,
        )
        return [RevenueSiteRolling(**r) for r in rows]

    @cached(ttl=600, prefix=_CACHE_PREFIX)
    def get_seasonality_monthly(self) -> list[SeasonalityMonthly]:
        """Monthly seasonal indices (cached 600s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_seasonality_monthly()
        return [SeasonalityMonthly(**r) for r in rows]

    @cached(ttl=600, prefix=_CACHE_PREFIX)
    def get_seasonality_daily(self) -> list[SeasonalityDaily]:
        """Day-of-week seasonal indices (cached 600s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_seasonality_daily()
        return [SeasonalityDaily(**r) for r in rows]

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_lifecycle(
        self,
        phase: str | None = None,
        limit: int = 50,
    ) -> list[ProductLifecycle]:
        """Product lifecycle classification (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_product_lifecycle(phase=phase, limit=limit)
        return [ProductLifecycle(**r) for r in rows]

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_lifecycle_distribution(self) -> LifecycleDistribution:
        """Distribution of products across lifecycle phases (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        data = self._feature_store_repo.get_lifecycle_distribution()
        return LifecycleDistribution(**data)
