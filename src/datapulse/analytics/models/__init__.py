"""Analytics response and filter models.

Split into per-domain files during the Phase 1 simplification sprint.
All imports through `datapulse.analytics.models` continue to work via
this barrel.
"""

from datapulse.analytics.models.breakdown import (
    BillingBreakdown,
    BillingBreakdownItem,
    BrandGroup,
    CategoryGroup,
    CustomerTypeBreakdown,
    CustomerTypeBreakdownItem,
    HeatmapCell,
    HeatmapData,
    LifecycleDistribution,
    ProductHierarchy,
    ProductInCategory,
    ProductLifecycle,
    RevenueDailyRolling,
    RevenueSiteRolling,
    SeasonalityDaily,
    SeasonalityMonthly,
)
from datapulse.analytics.models.churn import (
    ABCAnalysis,
    ABCItem,
    AffinityPair,
    ChurnPrediction,
    ReturnAnalysis,
    ReturnsTrend,
    ReturnsTrendPoint,
)
from datapulse.analytics.models.detail import (
    CustomerAnalytics,
    RevenueDriver,
    SiteDetail,
    WaterfallAnalysis,
)
from datapulse.analytics.models.health import (
    CustomerHealthScore,
    HealthDistribution,
)
from datapulse.analytics.models.kpi import (
    DashboardData,
    KPISummary,
    SegmentSummary,
    TrendResult,
)
from datapulse.analytics.models.ranking import (
    MoverItem,
    ProductPerformance,
    RankingItem,
    RankingResult,
    StaffPerformance,
    StaffQuota,
    TopMovers,
)
from datapulse.analytics.models.shared import (
    AnalyticsFilter,
    DataDateRange,
    DateRange,
    FilterOption,
    FilterOptions,
    StatisticalAnnotation,
    TimeSeriesPoint,
)

__all__ = [
    # breakdown
    "BillingBreakdown",
    "BillingBreakdownItem",
    "BrandGroup",
    "CategoryGroup",
    "CustomerTypeBreakdown",
    "CustomerTypeBreakdownItem",
    "HeatmapCell",
    "HeatmapData",
    "LifecycleDistribution",
    "ProductHierarchy",
    "ProductInCategory",
    "ProductLifecycle",
    "RevenueDailyRolling",
    "RevenueSiteRolling",
    "SeasonalityDaily",
    "SeasonalityMonthly",
    # churn
    "ABCAnalysis",
    "ABCItem",
    "AffinityPair",
    "ChurnPrediction",
    "ReturnAnalysis",
    "ReturnsTrend",
    "ReturnsTrendPoint",
    # detail
    "CustomerAnalytics",
    "RevenueDriver",
    "SiteDetail",
    "WaterfallAnalysis",
    # health
    "CustomerHealthScore",
    "HealthDistribution",
    # kpi
    "DashboardData",
    "KPISummary",
    "SegmentSummary",
    "TrendResult",
    # ranking
    "MoverItem",
    "ProductPerformance",
    "RankingItem",
    "RankingResult",
    "StaffPerformance",
    "StaffQuota",
    "TopMovers",
    # shared
    "AnalyticsFilter",
    "DataDateRange",
    "DateRange",
    "FilterOption",
    "FilterOptions",
    "StatisticalAnnotation",
    "TimeSeriesPoint",
]
