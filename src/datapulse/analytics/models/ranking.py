"""Ranking, top-N list, and staff performance models.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datapulse.analytics.models.shared import TimeSeriesPoint
from datapulse.types import JsonDecimal


class RankingItem(BaseModel):
    """Single item in a ranked list (product, customer, staff, site)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    key: int
    name: str
    value: JsonDecimal
    pct_of_total: JsonDecimal
    # Entity-specific enrichment. Populated only when the ranking source
    # has meaningful data for the field — e.g. ``staff_count`` is set for
    # site rankings (#507), left ``None`` elsewhere so existing consumers
    # are unaffected.
    staff_count: int | None = None


class RankingResult(BaseModel):
    """Ranked list with grand total for percentage calculations."""

    model_config = ConfigDict(frozen=True)

    items: list[RankingItem]
    total: JsonDecimal
    active_count: int | None = None


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


class StaffQuota(BaseModel):
    """Staff quota attainment for a given period."""

    model_config = ConfigDict(frozen=True)

    staff_key: int
    staff_name: str
    staff_position: str | None = None
    year: int
    month: int
    actual_revenue: JsonDecimal
    actual_transactions: int | None = None
    target_revenue: JsonDecimal | None = None
    target_transactions: JsonDecimal | None = None
    revenue_achievement_pct: JsonDecimal | None = None
    transactions_achievement_pct: JsonDecimal | None = None
    revenue_variance: JsonDecimal | None = None


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
