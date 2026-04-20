"""Composite revenue-forecast response models (#504).

Models combine actual + forecast + target into a single payload so the
dashboard revenue chart renders without orchestrating three SWR hooks.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.analytics.models.shared import TimeSeriesPoint
from datapulse.types import JsonDecimal


class ForecastBandPoint(BaseModel):
    """Forecast point carrying a confidence interval for the chart band."""

    model_config = ConfigDict(frozen=True)

    date: str  # ISO date "YYYY-MM-DD"
    value: JsonDecimal
    ci_low: JsonDecimal
    ci_high: JsonDecimal


class RevenueTarget(BaseModel):
    """Period-scoped target overlay (horizontal dashed line + status)."""

    model_config = ConfigDict(frozen=True)

    period_end: date
    value: JsonDecimal
    status: str  # "on_track" | "behind" | "ahead" | "unknown"


class RevenueForecastStats(BaseModel):
    """Summary stats shown above the chart."""

    model_config = ConfigDict(frozen=True)

    this_period_egp: JsonDecimal = Field(default=Decimal("0"))
    delta_pct: JsonDecimal | None = None
    confidence: int | None = None  # 0–100 mirrored from forecast MAPE


class RevenueForecast(BaseModel):
    """Composite payload for the dashboard revenue chart (#504).

    ``actual`` and ``forecast`` are disjoint — actual ends at ``today``,
    forecast begins the next period. The frontend chart overlays:

        * actual  (solid line + gradient fill)
        * forecast (dashed line + confidence band via ``ci_low``/``ci_high``)
        * target  (horizontal dashed reference line)
        * today   (vertical marker)
    """

    model_config = ConfigDict(frozen=True)

    actual: list[TimeSeriesPoint] = Field(default_factory=list)
    forecast: list[ForecastBandPoint] = Field(default_factory=list)
    target: RevenueTarget | None = None
    today: date
    period: str  # "day" | "week" | "month" | "quarter" | "ytd"
    stats: RevenueForecastStats = Field(default_factory=RevenueForecastStats)
