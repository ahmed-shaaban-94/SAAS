"""Pydantic models for what-if scenario analysis."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class ChangeType(StrEnum):
    percentage = "percentage"
    absolute = "absolute"


class AdjustmentParam(StrEnum):
    price = "price"
    volume = "volume"
    cost = "cost"


class Adjustment(BaseModel):
    """Single parameter adjustment for simulation."""

    model_config = ConfigDict(frozen=True)

    parameter: AdjustmentParam
    change_type: ChangeType = ChangeType.percentage
    change_value: float = Field(..., ge=-100, le=500)


class ScenarioInput(BaseModel):
    """Input for a what-if simulation."""

    model_config = ConfigDict(frozen=True)

    adjustments: list[Adjustment] = Field(..., min_length=1, max_length=5)
    months: int = Field(default=6, ge=1, le=24)


class TimePoint(BaseModel):
    """Single point in a scenario time series."""

    model_config = ConfigDict(frozen=True)

    month: str
    baseline: JsonDecimal
    projected: JsonDecimal


class ImpactSummary(BaseModel):
    """Summary of scenario impact."""

    model_config = ConfigDict(frozen=True)

    baseline_total: JsonDecimal
    projected_total: JsonDecimal
    absolute_change: JsonDecimal
    percentage_change: float


class ScenarioResult(BaseModel):
    """Result of a what-if simulation."""

    model_config = ConfigDict(frozen=True)

    revenue_series: list[TimePoint]
    margin_series: list[TimePoint]
    revenue_impact: ImpactSummary
    margin_impact: ImpactSummary
