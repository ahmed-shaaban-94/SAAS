"""Grouping / slicing breakdown models (by category, period, site, etc.).

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


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


class ProductLifecycle(BaseModel):
    """Product lifecycle classification: Growth, Mature, Decline, Dormant."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    drug_category: str
    avg_recent_growth: JsonDecimal | None = None
    quarters_active: int
    total_lifetime_revenue: JsonDecimal
    total_lifetime_quantity: JsonDecimal
    first_sale_quarter: str
    last_sale_quarter: str
    lifecycle_phase: str  # "Growth" | "Mature" | "Decline" | "Dormant"


class LifecycleDistribution(BaseModel):
    """Count of products in each lifecycle phase."""

    model_config = ConfigDict(frozen=True)

    growth: int = 0
    mature: int = 0
    decline: int = 0
    dormant: int = 0
    total: int = 0


class RevenueDailyRolling(BaseModel):
    """Daily revenue with rolling averages, volatility, and trend ratios."""

    model_config = ConfigDict(frozen=True)

    date_key: int
    full_date: date
    day_of_week: int
    is_weekend: bool
    daily_gross_amount: JsonDecimal
    daily_transactions: int
    daily_unique_customers: int
    ma_7d_revenue: JsonDecimal
    ma_30d_revenue: JsonDecimal
    ma_90d_revenue: JsonDecimal
    volatility_30d: JsonDecimal | None = None
    trend_ratio_7d_30d: JsonDecimal | None = None
    trend_ratio_30d_90d: JsonDecimal | None = None
    deviation_from_ma30: JsonDecimal | None = None
    same_day_last_week: JsonDecimal | None = None
    same_day_last_year: JsonDecimal | None = None


class RevenueSiteRolling(BaseModel):
    """Per-site daily rolling averages with cross-site comparison."""

    model_config = ConfigDict(frozen=True)

    date_key: int
    site_key: int
    full_date: date
    daily_gross_amount: JsonDecimal
    daily_transactions: int
    site_ma_7d: JsonDecimal
    site_ma_30d: JsonDecimal
    site_sum_30d: JsonDecimal
    site_vs_avg_ratio: JsonDecimal | None = None
    site_revenue_share: JsonDecimal | None = None


class SeasonalityMonthly(BaseModel):
    """Monthly seasonal index (12 rows per tenant)."""

    model_config = ConfigDict(frozen=True)

    month: int
    month_name: str
    avg_monthly_revenue: JsonDecimal
    avg_monthly_txn: JsonDecimal
    stddev_monthly_revenue: JsonDecimal | None = None
    years_of_data: int
    month_revenue_index: JsonDecimal
    month_txn_index: JsonDecimal


class SeasonalityDaily(BaseModel):
    """Day-of-week seasonal index (7 rows per tenant)."""

    model_config = ConfigDict(frozen=True)

    day_of_week: int
    day_name: str
    is_weekend: bool
    avg_revenue_by_dow: JsonDecimal
    avg_txn_by_dow: JsonDecimal
    avg_customers_by_dow: JsonDecimal
    stddev_revenue_by_dow: JsonDecimal | None = None
    sample_count: int
    dow_revenue_index: JsonDecimal
    dow_txn_index: JsonDecimal
