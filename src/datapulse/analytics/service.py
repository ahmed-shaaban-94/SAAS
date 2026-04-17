"""AnalyticsService — thin facade delegating to domain sub-services.

Public API is identical to the original monolithic service. All imports of
``from datapulse.analytics.service import AnalyticsService`` continue to
work without modification.

Domain sub-services:
- KPIService       : KPI summary, dashboard, date range, filter options
- RankingService   : trends, rankings, comparisons, advanced analytics
- BreakdownService : billing / customer-type breakdowns
- DetailService    : per-entity detail + feature store + lifecycle
- HealthService    : customer health scores
- ChurnService     : churn predictions + product affinity
"""

from __future__ import annotations

from datetime import date

from datapulse.analytics.advanced_repository import AdvancedRepository
from datapulse.analytics.affinity_repository import AffinityRepository
from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.churn_repository import ChurnRepository
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
from datapulse.analytics.services.breakdown import BreakdownService
from datapulse.analytics.services.churn import ChurnService
from datapulse.analytics.services.detail import DetailService
from datapulse.analytics.services.health import HealthService
from datapulse.analytics.services.kpi import KPIService
from datapulse.analytics.services.ranking import RankingService


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
        churn_repo: ChurnRepository | None = None,
        affinity_repo: AffinityRepository | None = None,
    ) -> None:
        self._repo = repo

        # Instantiate domain sub-services
        self._kpi = KPIService(repo=repo)
        self._ranking = RankingService(
            repo=repo,
            comparison_repo=comparison_repo,
            diagnostics_repo=diagnostics_repo,
            hierarchy_repo=hierarchy_repo,
            advanced_repo=advanced_repo,
        )
        self._breakdown = BreakdownService(repo=repo, breakdown_repo=breakdown_repo)
        self._detail = DetailService(
            detail_repo=detail_repo,
            feature_store_repo=feature_store_repo,
        )
        self._health = HealthService(customer_health_repo=customer_health_repo)
        self._churn = ChurnService(churn_repo=churn_repo, affinity_repo=affinity_repo)

    # ── KPI / Dashboard ──────────────────────────────────────────────────────

    def get_date_range(self) -> DataDateRange:
        return self._kpi.get_date_range()

    def get_dashboard_summary(self, target_date: date | None = None) -> KPISummary:
        return self._kpi.get_dashboard_summary(target_date)

    def get_filter_options(self) -> FilterOptions:
        return self._kpi.get_filter_options()

    def get_dashboard_data(
        self,
        target_date: date | None = None,
        filters: AnalyticsFilter | None = None,
    ) -> DashboardData:
        return self._kpi.get_dashboard_data(target_date, filters)

    # ── Trends ───────────────────────────────────────────────────────────────

    def get_revenue_trends(self, filters: AnalyticsFilter | None = None) -> dict[str, TrendResult]:
        return self._ranking.get_revenue_trends(filters)

    def get_daily_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        return self._ranking.get_daily_trend(filters)

    def get_monthly_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        return self._ranking.get_monthly_trend(filters)

    # ── Rankings ─────────────────────────────────────────────────────────────

    def get_product_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        return self._ranking.get_product_insights(filters)

    def get_customer_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        return self._ranking.get_customer_insights(filters)

    def get_site_comparison(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        return self._ranking.get_site_comparison(filters)

    def get_staff_leaderboard(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        return self._ranking.get_staff_leaderboard(filters)

    def get_origin_breakdown(self, filters: AnalyticsFilter | None = None) -> list[dict]:
        return self._ranking.get_origin_breakdown(filters)

    def get_return_report(self, filters: AnalyticsFilter | None = None) -> list[ReturnAnalysis]:
        return self._ranking.get_return_report(filters)

    # ── Comparison / Advanced ────────────────────────────────────────────────

    def get_top_movers(
        self,
        entity_type: str,
        filters: AnalyticsFilter | None = None,
        limit: int = 5,
    ) -> TopMovers:
        return self._ranking.get_top_movers(entity_type, filters, limit)

    def get_product_hierarchy(self, filters: AnalyticsFilter | None = None) -> ProductHierarchy:
        return self._ranking.get_product_hierarchy(filters)

    def get_abc_analysis(
        self, entity: str = "product", filters: AnalyticsFilter | None = None
    ) -> ABCAnalysis:
        return self._ranking.get_abc_analysis(entity, filters)

    def get_heatmap(self, year: int) -> HeatmapData:
        return self._ranking.get_heatmap(year)

    def get_returns_trend(self, filters: AnalyticsFilter | None = None) -> ReturnsTrend:
        return self._ranking.get_returns_trend(filters)

    def get_segment_summary(self) -> list[SegmentSummary]:
        return self._ranking.get_segment_summary()

    def get_why_changed(
        self,
        filters: AnalyticsFilter | None = None,
        limit: int = 15,
    ) -> WaterfallAnalysis:
        return self._ranking.get_why_changed(filters, limit)

    # ── Breakdown ────────────────────────────────────────────────────────────

    def get_billing_breakdown(self, filters: AnalyticsFilter | None = None) -> BillingBreakdown:
        return self._breakdown.get_billing_breakdown(filters)

    def get_customer_type_breakdown(
        self, filters: AnalyticsFilter | None = None
    ) -> CustomerTypeBreakdown:
        return self._breakdown.get_customer_type_breakdown(filters)

    # ── Detail ───────────────────────────────────────────────────────────────

    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        return self._detail.get_product_detail(product_key)

    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        return self._detail.get_customer_detail(customer_key)

    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        return self._detail.get_staff_detail(staff_key)

    def get_site_detail(self, site_key: int) -> SiteDetail | None:
        return self._detail.get_site_detail(site_key)

    # ── Feature Store ────────────────────────────────────────────────────────

    def get_revenue_daily_rolling(
        self,
        days: int = 90,
        limit: int = 200,
    ) -> list[RevenueDailyRolling]:
        return self._detail.get_revenue_daily_rolling(days, limit)

    def get_revenue_site_rolling(
        self,
        site_key: int | None = None,
        days: int = 30,
        limit: int = 200,
    ) -> list[RevenueSiteRolling]:
        return self._detail.get_revenue_site_rolling(site_key, days, limit)

    def get_seasonality_monthly(self) -> list[SeasonalityMonthly]:
        return self._detail.get_seasonality_monthly()

    def get_seasonality_daily(self) -> list[SeasonalityDaily]:
        return self._detail.get_seasonality_daily()

    def get_product_lifecycle(
        self,
        phase: str | None = None,
        limit: int = 50,
    ) -> list[ProductLifecycle]:
        return self._detail.get_product_lifecycle(phase, limit)

    def get_lifecycle_distribution(self) -> LifecycleDistribution:
        return self._detail.get_lifecycle_distribution()

    # ── Customer Health ──────────────────────────────────────────────────────

    def get_customer_health(
        self,
        band: str | None = None,
        limit: int = 50,
    ) -> list[CustomerHealthScore]:
        return self._health.get_customer_health(band, limit)

    def get_health_distribution(self) -> HealthDistribution:
        return self._health.get_health_distribution()

    def get_at_risk_customers(self, limit: int = 20) -> list[CustomerHealthScore]:
        return self._health.get_at_risk_customers(limit)

    # ── Churn & Affinity ─────────────────────────────────────────────────────

    def get_churn_predictions(
        self,
        risk_level: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self._churn.get_churn_predictions(risk_level, limit)

    def get_affinity_for_product(
        self,
        product_key: int,
        limit: int = 10,
    ) -> list[dict]:
        return self._churn.get_affinity_for_product(product_key, limit)
