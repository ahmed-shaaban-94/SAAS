"""Pydantic models for notification center."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
