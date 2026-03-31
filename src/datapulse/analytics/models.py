"""Pydantic response models for the analytics module.

All models are frozen (immutable) to prevent accidental mutation.
Financial values use Decimal for precision.
"""

from __future__ import annotations

from datetime import date

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


class TrendResult(BaseModel):
    """Aggregated time-series result with summary statistics."""

    model_config = ConfigDict(frozen=True)

    points: list[TimeSeriesPoint]
    total: JsonDecimal
    average: JsonDecimal
    minimum: JsonDecimal
    maximum: JsonDecimal
    growth_pct: JsonDecimal | None = None


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

    today_net: JsonDecimal
    mtd_net: JsonDecimal
    ytd_net: JsonDecimal
    mom_growth_pct: JsonDecimal | None = None
    yoy_growth_pct: JsonDecimal | None = None
    daily_transactions: int
    daily_customers: int
    avg_basket_size: JsonDecimal = Field(default=0)
    daily_returns: int = 0
    mtd_transactions: int = 0
    ytd_transactions: int = 0
    sparkline: list[TimeSeriesPoint] = Field(default_factory=list)


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
    """Single billing method with its share of total sales."""

    model_config = ConfigDict(frozen=True)

    billing_way: str
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
