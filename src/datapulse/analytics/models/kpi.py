"""KPI summary and dashboard response models.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.analytics.models.ranking import RankingResult
from datapulse.analytics.models.shared import (
    FilterOptions,
    StatisticalAnnotation,
    TimeSeriesPoint,
)
from datapulse.types import JsonDecimal


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
    # Units (quantity — returns are negative)
    daily_quantity: JsonDecimal = Field(default=Decimal("0"))
    daily_transactions: int
    daily_customers: int
    # Period-aware aliases — preferred names for new frontend consumers.
    # Legacy fields (today_gross / daily_transactions / daily_customers) are kept
    # for AI Light prompts, n8n workflows, and the mobile app.
    period_gross: JsonDecimal = Field(default=Decimal("0"))
    period_transactions: int = 0
    period_customers: int = 0
    avg_basket_size: JsonDecimal = Field(default=Decimal("0"))
    daily_returns: int = 0
    mtd_transactions: int = 0
    ytd_transactions: int = 0
    sparkline: list[TimeSeriesPoint] = Field(default_factory=list)
    mom_significance: str | None = None  # "significant" | "inconclusive" | "noise"
    yoy_significance: str | None = None


class SegmentSummary(BaseModel):
    """Summary of customer segments for the dashboard."""

    model_config = ConfigDict(frozen=True)

    segment: str
    count: int
    total_revenue: JsonDecimal
    avg_monetary: JsonDecimal
    avg_frequency: JsonDecimal
    pct_of_customers: JsonDecimal


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
