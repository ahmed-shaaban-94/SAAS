"""Pydantic models for AI-Light insights."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class InsightRequest(BaseModel):
    """Request body for generating AI insights."""

    model_config = ConfigDict(frozen=True)

    insight_type: str = Field(description="Type of insight: 'summary', 'anomalies', or 'changes'")
    start_date: date | None = None
    end_date: date | None = None


class AISummary(BaseModel):
    """AI-generated narrative summary of analytics data."""

    model_config = ConfigDict(frozen=True)

    narrative: str
    highlights: list[str]
    period: str


class Anomaly(BaseModel):
    """A detected anomaly in the data."""

    model_config = ConfigDict(frozen=True)

    date: str
    metric: str
    actual_value: JsonDecimal
    expected_range_low: JsonDecimal
    expected_range_high: JsonDecimal
    severity: str = Field(description="low, medium, or high")
    description: str


class AnomalyReport(BaseModel):
    """Collection of detected anomalies."""

    model_config = ConfigDict(frozen=True)

    anomalies: list[Anomaly]
    period: str
    total_checked: int


class ChangeDelta(BaseModel):
    """A single metric change between two periods."""

    model_config = ConfigDict(frozen=True)

    metric: str
    previous_value: JsonDecimal
    current_value: JsonDecimal
    change_pct: JsonDecimal
    direction: str  # "up", "down", "flat"


class ChangeNarrative(BaseModel):
    """AI-generated explanation of changes between periods."""

    model_config = ConfigDict(frozen=True)

    narrative: str
    deltas: list[ChangeDelta]
    current_period: str
    previous_period: str


class TopInsight(BaseModel):
    """Single headline insight for the dashboard AI alert banner (issue #510).

    Derived from the most severe active anomaly. When no active anomalies
    exist the route returns 204 rather than fabricating an insight — the
    banner simply hides.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    body: str
    action_label: str = "Investigate"
    action_target: str | None = None  # deep-link to anomaly/branch/etc.
    confidence: str  # "high" | "medium" | "low" | "info"
    generated_at: date
