"""POS desktop staged update rollout routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import CurrentUser, SessionDep, _tenant_id_of
from datapulse.pos.models import (
    DesktopUpdatePolicyResponse,
    DesktopUpdateReleaseRequest,
    DesktopUpdateReleaseResponse,
)
from datapulse.pos.update_policy import get_update_policy, list_releases, upsert_release
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


@router.get("/updates/policy", response_model=DesktopUpdatePolicyResponse)
@limiter.limit("30/minute")
def desktop_update_policy(
    request: Request,
    user: CurrentUser,
    session: SessionDep,
    current_version: Annotated[str, Query(min_length=1, max_length=50)] = "0.0.0",
    channel: Annotated[str, Query(min_length=1, max_length=40)] = "stable",
    platform: Annotated[str, Query(min_length=1, max_length=40)] = "win32",
) -> DesktopUpdatePolicyResponse:
    """Return whether this tenant may install a newer POS desktop release."""

    _ = request
    return get_update_policy(
        session,
        tenant_id=_tenant_id_of(user),
        current_version=current_version,
        channel=channel,
        platform=platform,
    )


@router.get(
    "/updates/releases",
    response_model=list[DesktopUpdateReleaseResponse],
    dependencies=[Depends(require_permission("pos:update:manage"))],
)
@limiter.limit("30/minute")
def list_desktop_update_releases(
    request: Request,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[DesktopUpdateReleaseResponse]:
    """List configured POS desktop update rollouts."""

    _ = request
    return list_releases(session, limit=limit)


@router.post(
    "/updates/releases",
    response_model=DesktopUpdateReleaseResponse,
    dependencies=[Depends(require_permission("pos:update:manage"))],
)
@limiter.limit("10/minute")
def upsert_desktop_update_release(
    request: Request,
    payload: DesktopUpdateReleaseRequest,
    session: SessionDep,
) -> DesktopUpdateReleaseResponse:
    """Create/update a release and choose all tenants or a selected tenant list."""

    _ = request
    return upsert_release(session, payload)
