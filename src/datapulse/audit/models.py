"""Pydantic models for the audit log."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    action: str
    endpoint: str
    method: str
    ip_address: str | None = None
    user_id: str | None = None
    response_status: int | None = None
    duration_ms: float | None = None
    created_at: datetime


class AuditLogPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
