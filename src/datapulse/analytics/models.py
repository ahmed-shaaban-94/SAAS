"""Pydantic response models for the analytics module.

All models are frozen (immutable) to prevent accidental mutation.
Financial values use Decimal for precision.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class DataDateRange(BaseModel):
    """Min/max dates of available data."""

    model_config = ConfigDict(frozen=True)

    min_date: date
    max_date: date


class DateRange(BaseModel):
    """Inclusive date range for filtering queries."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date


class AnalyticsFilter(BaseModel):
    """Common filter parameters accepted by all analytics queries."""

    model_config = ConfigDict(frozen=True)

    date_range: DateRange | None = None
    site_key: int | None = None
    category: str | None = None
    brand: str | None = None
    staff_key: int | None = None
    limit: int = Field(default=10, ge=1, le=100)


class TimeSeriesPoint(BaseModel):
    """Single data point in a time series (daily or monthly)."""

    model_config = ConfigDict(frozen=True)

    period: str  # "2024-01" or "2024-01-15"
    value: JsonDecimal


class StatisticalAnnotation(BaseModel):
    """Statistical confidence metadata for a metric or trend."""

    model_config = ConfigDict(frozen=True)

    z_score: JsonDecimal | None = None
    cv: JsonDecimal | None = None
    significance: str | None = None  # "significant" | "inconclusive" | "noise"


class TrendResult(BaseModel):
    """Aggregated time-series result with summary statistics."""

    model_config = ConfigDict(frozen=True)

    points: list[TimeSeriesPoint]
    total: JsonDecimal
    average: JsonDecimal
    minimum: JsonDecimal
    maximum: JsonDecimal
    growth_pct: JsonDecimal | None = None
    stats: StatisticalAnnotation | None = None


class RankingItem(BaseModel):
    """Single item in a ranked list (product, customer, staff, site)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    key: int
    name: str
    value: JsonDecimal
    pct_of_total: JsonDecimal


class RankingResult(BaseModel):
    """Ranked list with grand total for percentage calculations."""

    model_config = ConfigDict(frozen=True)

    items: list[RankingItem]
    total: JsonDecimal


class KPISummary(BaseModel):
    """Executive KPI snapshot for a given target date."""

    model_config = ConfigDict(frozen=True)

    # Gross sales (primary — net deliberately excluded from pipeline)
    today_gross: JsonDecimal
    mtd_gross: JsonDecimal
    ytd_gross: JsonDecimal
    # Discount (kept for future forecasting)
    today_discount: JsonDecimal = Field(default=Decimal("0"))
    # Growth (based on gross)
    mom_growth_pct: JsonDecimal | None = None
    yoy_growth_pct: JsonDecimal | None = None
    daily_transactions: int
    daily_customers: int
    avg_basket_size: JsonDecimal = Field(default=Decimal("0"))
    daily_returns: int = 0
    mtd_transactions: int = 0
    ytd_transactions: int = 0
    sparkline: list[TimeSeriesPoint] = Field(default_factory=list)
    mom_significance: str | None = None  # "significant" | "inconclusive" | "noise"
    yoy_significance: str | None = None


class ProductPerformance(BaseModel):
    """Detailed performance metrics for a single product."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    drug_category: str
    total_quantity: JsonDecimal
    total_sales: JsonDecimal
    total_net_amount: JsonDecimal
    return_rate: JsonDecimal
    unique_customers: int
    monthly_trend: list[TimeSeriesPoint] = []


class CustomerAnalytics(BaseModel):
    """Detailed analytics for a single customer."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_id: str
    customer_name: str
    total_quantity: JsonDecimal
    total_net_amount: JsonDecimal
    transaction_count: int
    unique_products: int
    return_count: int
    monthly_trend: list[TimeSeriesPoint] = []


class StaffPerformance(BaseModel):
    """Performance metrics for a single staff member."""

    model_config = ConfigDict(frozen=True)

    staff_key: int
    staff_id: str
    staff_name: str
    staff_position: str
    total_net_amount: JsonDecimal
    transaction_count: int
    avg_transaction_value: JsonDecimal
    unique_customers: int
    monthly_trend: list[TimeSeriesPoint] = []


class ReturnAnalysis(BaseModel):
    """Return/credit note analysis per product-customer pair."""

    model_config = ConfigDict(frozen=True)

    drug_name: str
    customer_name: str
    return_quantity: JsonDecimal
    return_amount: JsonDecimal
    return_count: int


class FilterOption(BaseModel):
    """Single key-label pair for dropdown/slicer population."""

    model_config = ConfigDict(frozen=True)

    key: int
    label: str


class FilterOptions(BaseModel):
    """Available filter values for all analytics slicers."""

    model_config = ConfigDict(frozen=True)

    categories: list[str]
    brands: list[str]
    sites: list[FilterOption]
    staff: list[FilterOption]


class DashboardData(BaseModel):
    """Composite dashboard payload — single request for the executive overview."""

    model_config = ConfigDict(frozen=True)

    kpi: KPISummary
    daily_trend: TrendResult
    monthly_trend: TrendResult
    top_products: RankingResult
    top_customers: RankingResult
    top_staff: RankingResult
    filter_options: FilterOptions


# ------------------------------------------------------------------
# Phase 2: Billing & Customer Type Analysis
# ------------------------------------------------------------------


class BillingBreakdownItem(BaseModel):
    """Single billing group with returns netted against sales."""

    model_config = ConfigDict(frozen=True)

    billing_group: str
    transaction_count: int
    total_net_amount: JsonDecimal
    pct_of_total: JsonDecimal


class BillingBreakdown(BaseModel):
    """Billing method distribution for a given filter range."""

    model_config = ConfigDict(frozen=True)

    items: list[BillingBreakdownItem]
    total_transactions: int
    total_net_amount: JsonDecimal


class CustomerTypeBreakdownItem(BaseModel):
    """Monthly customer type split: walk-in, insurance, other."""

    model_config = ConfigDict(frozen=True)

    period: str
    walk_in_count: int
    insurance_count: int
    other_count: int
    total_count: int


class CustomerTypeBreakdown(BaseModel):
    """Customer type distribution over time."""

    model_config = ConfigDict(frozen=True)

    items: list[CustomerTypeBreakdownItem]


# ------------------------------------------------------------------
# Phase 3: Comparative Analytics
# ------------------------------------------------------------------


class MoverItem(BaseModel):
    """Single entity in a top-movers list (gainer or loser)."""

    model_config = ConfigDict(frozen=True)

    key: int
    name: str
    current_value: JsonDecimal
    previous_value: JsonDecimal
    change_pct: JsonDecimal
    direction: str  # "up" or "down"


class TopMovers(BaseModel):
    """Top gainers and losers for a given entity type."""

    model_config = ConfigDict(frozen=True)

    gainers: list[MoverItem]
    losers: list[MoverItem]
    entity_type: str  # "product", "customer", "staff"


# ------------------------------------------------------------------
# Phase 4: Site Detail & Product Hierarchy
# ------------------------------------------------------------------


class SiteDetail(BaseModel):
    """Detailed metrics for a single site."""

    model_config = ConfigDict(frozen=True)

    site_key: int
    site_code: str
    site_name: str
    area_manager: str
    total_net_amount: JsonDecimal
    transaction_count: int
    unique_customers: int
    unique_staff: int
    walk_in_ratio: JsonDecimal
    insurance_ratio: JsonDecimal
    return_rate: JsonDecimal
    monthly_trend: list[TimeSeriesPoint] = Field(default_factory=list)


class ProductInCategory(BaseModel):
    """Single product within a brand group."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_name: str
    total_net_amount: JsonDecimal
    transaction_count: int


class BrandGroup(BaseModel):
    """Brand-level grouping within a category."""

    model_config = ConfigDict(frozen=True)

    brand: str
    total_net_amount: JsonDecimal
    products: list[ProductInCategory]


class CategoryGroup(BaseModel):
    """Top-level category grouping in the product hierarchy."""

    model_config = ConfigDict(frozen=True)

    category: str
    total_net_amount: JsonDecimal
    brands: list[BrandGroup]


class ProductHierarchy(BaseModel):
    """Hierarchical product view: Category > Brand > Product."""

    model_config = ConfigDict(frozen=True)

    categories: list[CategoryGroup]


# ------------------------------------------------------------------
# Phase 5: CEO Review — Advanced Analytics
# ------------------------------------------------------------------


class ABCItem(BaseModel):
    """Product classified by ABC analysis (revenue contribution)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    key: int
    name: str
    value: JsonDecimal
    cumulative_pct: JsonDecimal
    abc_class: str  # "A", "B", "C"


class ABCAnalysis(BaseModel):
    """ABC/Pareto analysis result."""

    model_config = ConfigDict(frozen=True)

    items: list[ABCItem]
    total: JsonDecimal
    class_a_count: int
    class_b_count: int
    class_c_count: int
    class_a_pct: JsonDecimal
    class_b_pct: JsonDecimal
    class_c_pct: JsonDecimal


class HeatmapCell(BaseModel):
    """Single cell in a calendar heatmap."""

    model_config = ConfigDict(frozen=True)

    date: str  # "2026-01-15"
    value: JsonDecimal


class HeatmapData(BaseModel):
    """Calendar heatmap data for revenue visualization."""

    model_config = ConfigDict(frozen=True)

    cells: list[HeatmapCell]
    min_value: JsonDecimal
    max_value: JsonDecimal


class ReturnsTrendPoint(BaseModel):
    """Returns trend data point."""

    model_config = ConfigDict(frozen=True)

    period: str
    return_count: int
    return_amount: JsonDecimal
    return_rate: JsonDecimal


class ReturnsTrend(BaseModel):
    """Returns trend over time."""

    model_config = ConfigDict(frozen=True)

    points: list[ReturnsTrendPoint]
    total_returns: int
    total_return_amount: JsonDecimal
    avg_return_rate: JsonDecimal


class SegmentSummary(BaseModel):
    """Summary of customer segments for the dashboard."""

    model_config = ConfigDict(frozen=True)

    segment: str
    count: int
    total_revenue: JsonDecimal
    avg_monetary: JsonDecimal
    avg_frequency: JsonDecimal
    pct_of_customers: JsonDecimal


# ------------------------------------------------------------------
# Enhancement 4: Analytics Intelligence
# ------------------------------------------------------------------


class RevenueDriver(BaseModel):
    """Single dimension-level driver of revenue change."""

    model_config = ConfigDict(frozen=True)

    dimension: str  # "product", "customer", "staff", "site"
    entity_key: int
    entity_name: str
    current_value: JsonDecimal
    previous_value: JsonDecimal
    impact: JsonDecimal  # current - previous (signed)
    impact_pct: JsonDecimal  # % of total change explained
    direction: str  # "positive" or "negative"


class WaterfallAnalysis(BaseModel):
    """Revenue change decomposition across dimensions."""

    model_config = ConfigDict(frozen=True)

    current_total: JsonDecimal
    previous_total: JsonDecimal
    total_change: JsonDecimal
    total_change_pct: JsonDecimal | None = None
    drivers: list[RevenueDriver]
    unexplained: JsonDecimal = Decimal("0")


class CustomerHealthScore(BaseModel):
    """Composite health score for a single customer."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_name: str
    health_score: JsonDecimal
    health_band: str  # "Thriving" | "Healthy" | "Needs Attention" | "At Risk" | "Critical"
    recency_days: int
    frequency_3m: int
    monetary_3m: JsonDecimal
    return_rate: JsonDecimal
    product_diversity: int
    trend: str  # "improving" | "stable" | "declining"


class HealthDistribution(BaseModel):
    """Distribution of customers across health bands."""

    model_config = ConfigDict(frozen=True)

    thriving: int = 0
    healthy: int = 0
    needs_attention: int = 0
    at_risk: int = 0
    critical: int = 0
    total: int = 0


class HealthMovement(BaseModel):
    """Customer movement between health bands."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_name: str
    from_band: str
    to_band: str
    score_change: JsonDecimal


class AnomalyAlert(BaseModel):
    """Detected anomaly in a metric."""

    model_config = ConfigDict(frozen=True)

    id: int = 0
    metric: str
    dimension: str | None = None
    dimension_key: int | None = None
    dimension_name: str | None = None
    period: date
    actual_value: JsonDecimal
    expected_value: JsonDecimal
    z_score: JsonDecimal | None = None
    severity: str  # "critical" | "high" | "medium" | "low"
    direction: str  # "spike" | "drop"
    is_suppressed: bool = False
    suppression_reason: str | None = None
    acknowledged: bool = False
