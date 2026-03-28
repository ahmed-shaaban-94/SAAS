"""Pydantic models for pipeline run tracking.

All models are frozen (immutable) to prevent accidental mutation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

JsonDecimal = Annotated[Decimal, PlainSerializer(float, return_type=float)]

VALID_STATUSES = frozenset({
    "pending",
    "running",
    "bronze_complete",
    "silver_complete",
    "gold_complete",
    "success",
    "failed",
})


class PipelineRunCreate(BaseModel):
    """Request body for creating a new pipeline run."""

    model_config = ConfigDict(frozen=True)

    run_type: str
    trigger_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineRunUpdate(BaseModel):
    """Request body for updating an existing pipeline run."""

    model_config = ConfigDict(frozen=True)

    status: str | None = None
    finished_at: datetime | None = None
    duration_seconds: JsonDecimal | None = None
    rows_loaded: int | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


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


class TriggerRequest(BaseModel):
    """Request body for triggering a full pipeline run."""

    model_config = ConfigDict(frozen=True)

    source_dir: str = "/app/data/raw/sales"
    tenant_id: int = 1

    @field_validator("source_dir")
    @classmethod
    def _jail_source_dir(cls, v: str) -> str:
        """Prevent path traversal — source_dir must be inside /app/data."""
        from pathlib import PurePosixPath

        normalized = PurePosixPath(v)
        if ".." in normalized.parts:
            raise ValueError("source_dir must not contain '..'")
        allowed_root = PurePosixPath("/app/data")
        if not str(normalized).startswith(str(allowed_root)):
            raise ValueError(f"source_dir must be inside {allowed_root}")
        return str(normalized)


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
        from pathlib import PurePosixPath

        normalized = PurePosixPath(v)
        if ".." in normalized.parts:
            raise ValueError("source_dir must not contain '..'")
        allowed_root = PurePosixPath("/app/data")
        if not str(normalized).startswith(str(allowed_root)):
            raise ValueError(f"source_dir must be inside {allowed_root}")
        return str(normalized)


class ExecutionResult(BaseModel):
    """Result from a pipeline stage execution."""

    model_config = ConfigDict(frozen=True)

    success: bool
    rows_loaded: int | None = None
    error: str | None = None
    duration_seconds: float
