"""Pydantic models for async query API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class QueryStatus(StrEnum):
    """Lifecycle states for an async query."""

    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class QuerySubmit(BaseModel):
    """Request body for submitting an async query."""

    sql: str = Field(..., min_length=1, max_length=10_000, description="SQL SELECT statement")
    row_limit: int = Field(10_000, ge=1, le=100_000, description="Max rows to return")


class QueryResponse(BaseModel):
    """Response after submitting a query (before results are ready)."""

    query_id: str
    status: QueryStatus
    submitted_at: datetime


class QueryResult(BaseModel):
    """Full query result (returned when status is complete)."""

    query_id: str
    status: QueryStatus
    submitted_at: datetime
    completed_at: datetime | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    duration_ms: float | None = None
    error: str | None = None
