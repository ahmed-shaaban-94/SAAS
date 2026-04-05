"""Pydantic models for saved views."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SavedViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    page_path: str = Field(default="/dashboard")
    filters: dict = Field(default_factory=dict)
    is_default: bool = False


class SavedViewUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    filters: dict | None = None
    is_default: bool | None = None


class SavedViewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    page_path: str
    filters: dict
    is_default: bool
    created_at: datetime
