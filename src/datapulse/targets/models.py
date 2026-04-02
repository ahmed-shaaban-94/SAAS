"""Pydantic models for targets & alerts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class TargetCreate(BaseModel):
    """Input model for creating a sales target."""

    target_type: str  # 'revenue', 'transactions', 'customers'
    granularity: str  # 'daily', 'monthly', 'yearly'
    period: str
    target_value: JsonDecimal
    entity_type: str | None = None
    entity_key: int | None = None


class TargetResponse(BaseModel):
    """Response model for a persisted sales target."""

    model_config = ConfigDict(frozen=True)

    id: int
    target_type: str
    granularity: str
    period: str
    target_value: JsonDecimal
    entity_type: str | None = None
    entity_key: int | None = None
    created_at: datetime
    updated_at: datetime


class TargetVsActual(BaseModel):
    """Single period comparison of target vs actual performance."""

    model_config = ConfigDict(frozen=True)

    period: str
    target_value: JsonDecimal
    actual_value: JsonDecimal
    variance: JsonDecimal
    achievement_pct: JsonDecimal


class TargetSummary(BaseModel):
    """Aggregated target vs actual summary with YTD totals."""

    model_config = ConfigDict(frozen=True)

    monthly_targets: list[TargetVsActual]
    ytd_target: JsonDecimal = Field(default=Decimal("0"))
    ytd_actual: JsonDecimal = Field(default=Decimal("0"))
    ytd_achievement_pct: JsonDecimal = Field(default=Decimal("0"))


class AlertConfigCreate(BaseModel):
    """Input model for creating an alert configuration."""

    alert_name: str
    metric: str
    condition: str  # 'below', 'above', 'change_pct'
    threshold: JsonDecimal
    entity_type: str | None = None
    entity_key: int | None = None
    enabled: bool = True
    notify_channels: list[str] = Field(default_factory=lambda: ["dashboard"])


class AlertConfigResponse(BaseModel):
    """Response model for a persisted alert configuration."""

    model_config = ConfigDict(frozen=True)

    id: int
    alert_name: str
    metric: str
    condition: str
    threshold: JsonDecimal
    entity_type: str | None = None
    entity_key: int | None = None
    enabled: bool
    notify_channels: list[str]
    created_at: datetime


class AlertLogResponse(BaseModel):
    """Response model for an alert log entry."""

    model_config = ConfigDict(frozen=True)

    id: int
    alert_config_id: int | None
    alert_name: str = ""
    fired_at: datetime
    metric_value: JsonDecimal | None = None
    threshold_value: JsonDecimal | None = None
    message: str | None = None
    acknowledged: bool
