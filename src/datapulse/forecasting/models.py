"""Pydantic response models for the forecasting module.

All models are frozen (immutable). Financial values use JsonDecimal for precision.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class ForecastPoint(BaseModel):
    """Single forecast data point."""

    model_config = ConfigDict(frozen=True)

    period: str  # "2026-04-03" or "2026-05"
    value: JsonDecimal
    lower_bound: JsonDecimal
    upper_bound: JsonDecimal


class ForecastAccuracy(BaseModel):
    """Accuracy metrics from backtesting."""

    model_config = ConfigDict(frozen=True)

    mape: JsonDecimal  # Mean Absolute Percentage Error
    mae: JsonDecimal  # Mean Absolute Error
    rmse: JsonDecimal  # Root Mean Squared Error
    coverage: JsonDecimal  # % of actuals within confidence interval


class ForecastResult(BaseModel):
    """Complete forecast for one entity."""

    model_config = ConfigDict(frozen=True)

    entity_type: str  # "revenue", "product"
    entity_key: int | None = None  # product_key if product, None for revenue
    method: str  # "holt_winters", "seasonal_naive", "sma"
    horizon: int  # number of periods forecasted
    granularity: str  # "daily" or "monthly"
    points: list[ForecastPoint]
    accuracy_metrics: ForecastAccuracy | None = None


class ProductForecastSummary(BaseModel):
    """Brief product forecast info for the summary view."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_name: str
    forecast_change_pct: JsonDecimal


class ForecastSummary(BaseModel):
    """Overview for the forecasting dashboard card."""

    model_config = ConfigDict(frozen=True)

    last_run_at: datetime | None = None
    next_30d_revenue: JsonDecimal = Field(default=Decimal("0"))
    next_3m_revenue: JsonDecimal = Field(default=Decimal("0"))
    revenue_trend: str = "stable"  # "up", "down", "stable"
    mape: JsonDecimal | None = None
    top_growing_products: list[ProductForecastSummary] = Field(default_factory=list)
    top_declining_products: list[ProductForecastSummary] = Field(default_factory=list)


class CustomerSegment(BaseModel):
    """Customer RFM segment from the feature store."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_id: str
    customer_name: str
    rfm_segment: str
    r_score: int
    f_score: int
    m_score: int
    days_since_last: int
    frequency: int
    monetary: JsonDecimal
    avg_basket_size: JsonDecimal
    return_rate: JsonDecimal
