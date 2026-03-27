"""Pydantic response models for the analytics module.

All models are frozen (immutable) to prevent accidental mutation.
Financial values use Decimal for precision.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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
    value: Decimal


class TrendResult(BaseModel):
    """Aggregated time-series result with summary statistics."""

    model_config = ConfigDict(frozen=True)

    points: list[TimeSeriesPoint]
    total: Decimal
    average: Decimal
    minimum: Decimal
    maximum: Decimal
    growth_pct: Decimal | None = None


class RankingItem(BaseModel):
    """Single item in a ranked list (product, customer, staff, site)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    key: int
    name: str
    value: Decimal
    pct_of_total: Decimal


class RankingResult(BaseModel):
    """Ranked list with grand total for percentage calculations."""

    model_config = ConfigDict(frozen=True)

    items: list[RankingItem]
    total: Decimal


class KPISummary(BaseModel):
    """Executive KPI snapshot for a given target date."""

    model_config = ConfigDict(frozen=True)

    today_net: Decimal
    mtd_net: Decimal
    ytd_net: Decimal
    mom_growth_pct: Decimal | None = None
    yoy_growth_pct: Decimal | None = None
    daily_transactions: int
    daily_customers: int


class ProductPerformance(BaseModel):
    """Detailed performance metrics for a single product."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    drug_category: str
    total_quantity: Decimal
    total_sales: Decimal
    total_net_amount: Decimal
    return_rate: Decimal
    unique_customers: int


class CustomerAnalytics(BaseModel):
    """Detailed analytics for a single customer."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_id: str
    customer_name: str
    total_quantity: Decimal
    total_net_amount: Decimal
    transaction_count: int
    unique_products: int
    return_count: int


class StaffPerformance(BaseModel):
    """Performance metrics for a single staff member."""

    model_config = ConfigDict(frozen=True)

    staff_key: int
    staff_id: str
    staff_name: str
    staff_position: str
    total_net_amount: Decimal
    transaction_count: int
    avg_transaction_value: Decimal
    unique_customers: int


class ReturnAnalysis(BaseModel):
    """Return/credit note analysis per product-customer pair."""

    model_config = ConfigDict(frozen=True)

    drug_name: str
    customer_name: str
    return_quantity: Decimal
    return_amount: Decimal
    return_count: int
