"""Pydantic models for notification center."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    type: str
    title: str
    message: str
    link: str | None = None
    read: bool
    created_at: datetime


class NotificationCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    unread: int


class CreateNotification(BaseModel):
    type: str = Field(..., pattern="^(urgent|info|success)$")
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    link: str | None = None
    user_id: str | None = None
