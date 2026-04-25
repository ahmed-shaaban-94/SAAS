"""POS desktop update rollout models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RolloutScope = Literal["all", "selected", "paused"]


class DesktopUpdatePolicyResponse(BaseModel):
    """Tenant-specific answer consumed by the Electron auto-updater gate."""

    model_config = ConfigDict(frozen=True)

    update_available: bool
    allowed: bool
    reason: str
    version: str | None = None
    channel: str | None = None
    platform: str | None = None
    release_id: int | None = None
    rollout_scope: RolloutScope | None = None
    release_notes: str | None = None


class DesktopUpdateReleaseRequest(BaseModel):
    """Create or replace a desktop release rollout."""

    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1, max_length=50)
    channel: str = Field(default="stable", min_length=1, max_length=40)
    platform: str = Field(default="win32", min_length=1, max_length=40)
    rollout_scope: RolloutScope = "selected"
    active: bool = True
    tenant_ids: list[int] = Field(default_factory=list)
    release_notes: str | None = Field(default=None, max_length=4000)
    min_schema_version: int | None = Field(default=None, ge=1)
    max_schema_version: int | None = Field(default=None, ge=1)
    min_app_version: str | None = Field(default=None, max_length=50)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("tenant_ids")
    @classmethod
    def _dedupe_tenant_ids(cls, value: list[int]) -> list[int]:
        return sorted(set(value))


class DesktopUpdateReleaseResponse(BaseModel):
    """Admin-facing release rollout record."""

    model_config = ConfigDict(frozen=True)

    release_id: int
    version: str
    channel: str
    platform: str
    rollout_scope: RolloutScope
    active: bool
    tenant_ids: list[int]
    release_notes: str | None = None
    min_schema_version: int | None = None
    max_schema_version: int | None = None
    min_app_version: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
