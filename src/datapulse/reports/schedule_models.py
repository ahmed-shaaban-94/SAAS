"""Pydantic models for report schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReportScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    report_type: str  # 'dashboard', 'products', 'customers', 'staff'
    cron_expression: str = Field(..., min_length=1, max_length=100)
    recipients: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    report_type: str
    cron_expression: str
    recipients: list[str]
    parameters: dict[str, Any]
    enabled: bool
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReportScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    recipients: list[str] | None = None
    parameters: dict[str, Any] | None = None
    enabled: bool | None = None
