"""Single-entity detail response models.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.analytics.models.shared import TimeSeriesPoint
from datapulse.types import JsonDecimal


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
