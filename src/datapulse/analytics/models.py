"""Pydantic response models for the analytics module.

All models are frozen (immutable) to prevent accidental mutation.
Financial values use Decimal for precision.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# Decimal that serializes as a JSON number (float) instead of a string.
# WARNING: Decimal->float conversion may lose precision for values exceeding
# Number.MAX_SAFE_INTEGER (2^53). Financial totals in the billions are safe,
# but if values reach ~9 quadrillion the least-significant digits will be lost.
JsonDecimal = Annotated[Decimal, PlainSerializer(float, return_type=float)]


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


class FilterOption(BaseModel):
    """A single selectable filter option (e.g. a site or staff member)."""

    model_config = ConfigDict(frozen=True)

    key: int
    label: str


class FilterOptions(BaseModel):
    """Available filter values for slicer/dropdown population."""

    model_config = ConfigDict(frozen=True)

    categories: list[str]
    brands: list[str]
    sites: list[FilterOption]
    staff: list[FilterOption]


class ReturnAnalysis(BaseModel):
    """Return/credit note analysis per product-customer pair."""

    model_config = ConfigDict(frozen=True)

    drug_name: str
    customer_name: str
    return_quantity: JsonDecimal
    return_amount: JsonDecimal
    return_count: int
