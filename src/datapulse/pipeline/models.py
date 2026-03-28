"""Pydantic models for pipeline run tracking.

All models are frozen (immutable) to prevent accidental mutation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

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
