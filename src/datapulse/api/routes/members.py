"""User management & RBAC API routes — members, roles, sectors."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from datapulse.api.deps import CurrentUser
from datapulse.api.limiter import limiter
from datapulse.rbac.dependencies import (
    AccessCtx,
    get_rbac_service,
    require_permission,
    require_role,
)
from datapulse.rbac.models import (
    MemberBrief,
    MemberInvite,
    MemberResponse,
    MemberUpdate,
    RoleWithPermissions,
    SectorCreate,
    SectorResponse,
    SectorUpdate,
)
from datapulse.rbac.service import RBACService

logger = structlog.get_logger()

router = APIRouter(prefix="/members", tags=["members"])

# ── Access Context (current user) ────────────────────────────


@router.get("/me")
def get_my_access(ctx: AccessCtx) -> dict:
    """Return the current user's access context — role, permissions, sectors."""
    return {
        "member_id": ctx.member_id,
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "role_key": ctx.role_key,
        "permissions": sorted(ctx.permissions),
        "sector_ids": ctx.sector_ids,
        "site_codes": ctx.site_codes,
        "is_admin": ctx.is_admin,
        "has_full_access": ctx.has_full_access,
    }


# ── Roles ────────────────────────────────────────────────────


@router.get("/roles", response_model=list[RoleWithPermissions])
def list_roles(
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
) -> list[RoleWithPermissions]:
    """List all available roles with their permissions."""
    return service.list_roles()


# ── Members ──────────────────────────────────────────────────


@router.get("", response_model=list[MemberResponse])
def list_members(
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("members:view"))],
) -> list[MemberResponse]:
    """List all members in the tenant. Requires members:view permission."""
    return service.list_members(ctx.tenant_id)


@router.post("", response_model=MemberResponse, status_code=201)
@limiter.limit("10/minute")
def invite_member(
    request: Request,
    body: MemberInvite,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("members:manage"))],
) -> MemberResponse:
    """Invite a new member to the tenant. Requires members:manage permission."""
    try:
        return service.invite_member(ctx.tenant_id, body, invited_by=ctx.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{member_id}", response_model=MemberResponse)
@limiter.limit("20/minute")
def update_member(
    request: Request,
    member_id: int,
    body: MemberUpdate,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("members:manage"))],
) -> MemberResponse:
    """Update a member's role, name, status, or sector access."""
    try:
        return service.update_member(member_id, body, actor_role=ctx.role_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{member_id}", status_code=204)
@limiter.limit("10/minute")
def remove_member(
    request: Request,
    member_id: int,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("members:manage"))],
) -> None:
    """Remove a member from the tenant."""
    try:
        service.remove_member(member_id, actor_member_id=ctx.member_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── Sectors ──────────────────────────────────────────────────

sectors_router = APIRouter(prefix="/sectors", tags=["sectors"])


@sectors_router.get("", response_model=list[SectorResponse])
def list_sectors(
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
) -> list[SectorResponse]:
    """List all sectors in the tenant. Any authenticated member can view."""
    return service.list_sectors(ctx.tenant_id)


@sectors_router.post("", response_model=SectorResponse, status_code=201)
@limiter.limit("10/minute")
def create_sector(
    request: Request,
    body: SectorCreate,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("sectors:manage"))],
) -> SectorResponse:
    """Create a new sector. Requires sectors:manage permission."""
    try:
        return service.create_sector(ctx.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@sectors_router.patch("/{sector_id}", response_model=SectorResponse)
@limiter.limit("20/minute")
def update_sector(
    request: Request,
    sector_id: int,
    body: SectorUpdate,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("sectors:manage"))],
) -> SectorResponse:
    """Update a sector's name, description, site_codes, or status."""
    try:
        return service.update_sector(sector_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@sectors_router.delete("/{sector_id}", status_code=204)
@limiter.limit("10/minute")
def delete_sector(
    request: Request,
    sector_id: int,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
    _: Annotated[None, Depends(require_permission("sectors:manage"))],
) -> None:
    """Delete a sector."""
    try:
        service.delete_sector(sector_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@sectors_router.get("/{sector_id}/members", response_model=list[MemberBrief])
def get_sector_members(
    sector_id: int,
    ctx: AccessCtx,
    service: Annotated[RBACService, Depends(get_rbac_service)],
) -> list[MemberBrief]:
    """List members assigned to a sector."""
    members = service.get_sector_members(sector_id)
    return [MemberBrief(**m) for m in members]
