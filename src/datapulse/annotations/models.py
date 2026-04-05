"""Pydantic models for chart annotations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnnotationCreate(BaseModel):
    chart_id: str = Field(..., min_length=1, max_length=100)
    data_point: str = Field(..., min_length=1, max_length=100)
    note: str = Field(..., min_length=1, max_length=500)
    color: str = Field(default="#D97706", pattern="^#[0-9A-Fa-f]{6}$")


class AnnotationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    chart_id: str
    data_point: str
    note: str
    color: str
    user_id: str
    created_at: datetime
