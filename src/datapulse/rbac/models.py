"""Pydantic models for RBAC — roles, permissions, members, sectors."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ── Roles & Permissions ──────────────────────────────────────

RoleKey = Literal["owner", "admin", "editor", "viewer"]


class RoleResponse(BaseModel):
    role_id: int
    role_key: RoleKey
    role_name: str
    description: str
    is_system: bool


class PermissionResponse(BaseModel):
    permission_key: str
    category: str
    description: str


class RoleWithPermissions(RoleResponse):
    permissions: list[str] = Field(default_factory=list)


# ── Tenant Members ───────────────────────────────────────────


class MemberInvite(BaseModel):
    email: EmailStr
    display_name: str = ""
    role_key: RoleKey = "viewer"
    sector_ids: list[int] = Field(default_factory=list)


class MemberUpdate(BaseModel):
    role_key: RoleKey | None = None
    display_name: str | None = None
    is_active: bool | None = None
    sector_ids: list[int] | None = None


class MemberResponse(BaseModel):
    member_id: int
    tenant_id: int
    user_id: str
    email: str
    display_name: str
    role_key: RoleKey
    role_name: str
    is_active: bool
    invited_by: str | None
    invited_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    sectors: list[SectorBrief] = Field(default_factory=list)


class MemberBrief(BaseModel):
    member_id: int
    email: str
    display_name: str
    role_key: RoleKey
    is_active: bool


# ── Sectors ──────────────────────────────────────────────────


class SectorCreate(BaseModel):
    sector_key: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    sector_name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    site_codes: list[str] = Field(default_factory=list)


class SectorUpdate(BaseModel):
    sector_name: str | None = None
    description: str | None = None
    site_codes: list[str] | None = None
    is_active: bool | None = None


class SectorResponse(BaseModel):
    sector_id: int
    tenant_id: int
    sector_key: str
    sector_name: str
    description: str
    site_codes: list[str]
    is_active: bool
    created_at: datetime
    member_count: int = 0


class SectorBrief(BaseModel):
    sector_id: int
    sector_key: str
    sector_name: str


# Rebuild forward refs for MemberResponse
MemberResponse.model_rebuild()


# ── Access Check Result ──────────────────────────────────────


class AccessContext(BaseModel):
    """Resolved access context for the current user within a tenant."""

    member_id: int
    tenant_id: int
    user_id: str
    role_key: RoleKey
    permissions: set[str] = Field(default_factory=set)
    sector_ids: list[int] = Field(default_factory=list)
    site_codes: list[str] = Field(default_factory=list)
    is_admin: bool = False

    @property
    def has_full_access(self) -> bool:
        """Owners and admins bypass sector filtering."""
        return self.role_key in ("owner", "admin")
