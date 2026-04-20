"""Pydantic models for pipeline run tracking.

All models are frozen (immutable) to prevent accidental mutation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datapulse.types import JsonDecimal, validate_source_dir

VALID_STATUSES = frozenset(
    {
        "pending",
        "running",
        "bronze_complete",
        "silver_complete",
        "gold_complete",
        "success",
        "failed",
    }
)


VALID_RUN_TYPES = frozenset({"full", "bronze", "staging", "marts"})


class PipelineRunCreate(BaseModel):
    """Request body for creating a new pipeline run."""

    model_config = ConfigDict(frozen=True)

    run_type: str
    trigger_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_type")
    @classmethod
    def _validate_run_type(cls, v: str) -> str:
        if v not in VALID_RUN_TYPES:
            raise ValueError(
                f"Invalid run_type '{v}'. Must be one of: {', '.join(sorted(VALID_RUN_TYPES))}"
            )
        return v


class PipelineRunUpdate(BaseModel):
    """Request body for updating an existing pipeline run."""

    model_config = ConfigDict(frozen=True)

    status: str | None = None
    finished_at: datetime | None = None
    duration_seconds: JsonDecimal | None = None
    rows_loaded: int | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    last_completed_stage: str | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )
        return v


class PipelineRunResponse(BaseModel):
    """Single pipeline run returned by the API."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    tenant_id: int
    run_type: str
    status: str
    trigger_source: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: JsonDecimal | None
    rows_loaded: int | None
    error_message: str | None
    metadata: dict[str, Any]


class PipelineRunList(BaseModel):
    """Paginated list of pipeline runs."""

    model_config = ConfigDict(frozen=True)

    items: list[PipelineRunResponse]
    total: int
    offset: int
    limit: int


# ────────────────────────────────────────────────────────────────────────
# Dashboard health composite (#509)
# ────────────────────────────────────────────────────────────────────────


class PipelineHealthNode(BaseModel):
    """Single medallion node (bronze/silver/gold) in the health card."""

    model_config = ConfigDict(frozen=True)

    label: str  # "Bronze" | "Silver" | "Gold"
    value: str  # human-readable summary (e.g. "1.13M rows", "Running...", "47 marts")
    status: str  # "ok" | "running" | "pending" | "failed"


class PipelineHealthRun(BaseModel):
    """Last-run summary (timestamp + duration)."""

    model_config = ConfigDict(frozen=True)

    at: datetime
    duration_seconds: JsonDecimal | None = None


class PipelineHealthCounter(BaseModel):
    """Generic passed/total counter (quality gates, dbt tests)."""

    model_config = ConfigDict(frozen=True)

    passed: int
    total: int


class PipelineHealthHistoryPoint(BaseModel):
    """A single day on the 7-day run history bar chart."""

    model_config = ConfigDict(frozen=True)

    date: str  # ISO "YYYY-MM-DD"
    duration_seconds: JsonDecimal | None = None
    status: str  # "ok" | "warning" | "fail" | "none"


class PipelineHealth(BaseModel):
    """Composite pipeline health payload for the dashboard card (#509).

    Single tidy response combining medallion node status, last/next run
    pointers, quality counters, and the 7-day duration history — saving
    the frontend three extra round-trips.
    """

    model_config = ConfigDict(frozen=True)

    nodes: list[PipelineHealthNode]
    last_run: PipelineHealthRun | None = None
    next_run_at: datetime | None = None
    gates: PipelineHealthCounter
    tests: PipelineHealthCounter
    history_7d: list[PipelineHealthHistoryPoint]


class TriggerRequest(BaseModel):
    """Request body for triggering a full pipeline run."""

    model_config = ConfigDict(frozen=True)

    source_dir: str = "/app/data/raw/sales"
    tenant_id: int = 1

    @field_validator("source_dir")
    @classmethod
    def _jail_source_dir(cls, v: str) -> str:
        """Prevent path traversal — source_dir must be inside /app/data."""
        return validate_source_dir(v)


class TriggerResponse(BaseModel):
    """Response from the trigger endpoint."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    status: str


class ExecuteRequest(BaseModel):
    """Request body for individual pipeline stage execution."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    source_dir: str = "/app/data/raw/sales"
    tenant_id: int = 1

    @field_validator("source_dir")
    @classmethod
    def _jail_source_dir(cls, v: str) -> str:
        """Prevent path traversal — source_dir must be inside /app/data."""
        return validate_source_dir(v)


class ExecutionResult(BaseModel):
    """Result from a pipeline stage execution."""

    model_config = ConfigDict(frozen=True)

    success: bool
    rows_loaded: int | None = None
    error: str | None = None
    duration_seconds: float


class RunScore(BaseModel):
    """Quality score for a single pipeline run."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    run_type: str
    status: str
    started_at: datetime
    total_checks: int
    passed: int
    failed: int
    warned: int
    pass_rate: float


class QualityScorecard(BaseModel):
    """Aggregated quality scorecard across recent pipeline runs."""

    model_config = ConfigDict(frozen=True)

    runs: list[RunScore]
    overall_pass_rate: float
    total_runs: int
