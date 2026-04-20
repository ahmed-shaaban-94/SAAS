"""Pydantic models for anomaly detection."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


class AnomalyDetectionConfig(BaseModel):
    """Thresholds for anomaly severity classification."""

    critical_z: float = 3.5
    high_z: float = 3.0
    medium_z: float = 2.5
    low_z: float = 2.0
    lookback_days: int = 90
    min_data_points: int = 14


class DetectedAnomaly(BaseModel):
    """Raw anomaly detection result (before persistence)."""

    model_config = ConfigDict(frozen=True)

    metric: str
    period: date
    actual_value: JsonDecimal
    expected_value: JsonDecimal
    lower_bound: JsonDecimal
    upper_bound: JsonDecimal
    z_score: JsonDecimal | None = None
    severity: str  # "critical" | "high" | "medium" | "low"
    direction: str  # "spike" | "drop"
    is_suppressed: bool = False
    suppression_reason: str | None = None


class AnomalyAlertResponse(BaseModel):
    """Persisted anomaly alert for API responses."""

    model_config = ConfigDict(frozen=True)

    id: int
    metric: str
    period: date
    actual_value: JsonDecimal
    expected_value: JsonDecimal
    z_score: JsonDecimal | None = None
    severity: str
    direction: str
    is_suppressed: bool = False
    suppression_reason: str | None = None
    acknowledged: bool = False


class AnomalyRunResult(BaseModel):
    """Summary of an anomaly detection run."""

    model_config = ConfigDict(frozen=True)

    total_checked: int
    anomalies_found: int
    suppressed: int
    alerts_saved: int


class AnomalyCard(BaseModel):
    """Display-ready projection for the dashboard anomaly feed widget (#508).

    Maps the raw ``AnomalyAlertResponse`` onto the shape the new design
    expects — a kind/title/body/time_ago/confidence quintet — so the
    frontend renders cards without extra transformation.
    """

    model_config = ConfigDict(frozen=True)

    id: int
    kind: str  # "up" | "down" | "info"
    title: str
    body: str
    time_ago: str
    confidence: str  # "high" | "medium" | "low" | "info"
