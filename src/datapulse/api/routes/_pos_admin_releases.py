"""Admin: register a POS desktop release in the staged-rollout table.

Sub-router for ``pos.py``. Replaces the per-release SQL migration
pattern (#802 used migration 123) with an authenticated HTTP entry
point that the ``pos-desktop-release`` workflow calls after a
successful publish to GitHub Releases.

RBAC: ``pos:update:manage`` (granted to owner / admin / pos_manager
in migration 115). The service-account token used by CI must belong
to a tenant on the platform or enterprise plan — the parent
``pos.router`` enforces ``require_pos_plan()`` for every sub-route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import SessionDep
from datapulse.pos.admin_release_service import upsert_release
from datapulse.pos.models.admin_release import (
    DesktopReleaseCreate,
    DesktopReleaseResponse,
)
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


@router.post(
    "/admin/desktop-releases",
    response_model=DesktopReleaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("pos:update:manage"))],
)
@limiter.limit("10/minute")
def post_desktop_release(
    request: Request,
    payload: DesktopReleaseCreate,
    session: SessionDep,
) -> DesktopReleaseResponse:
    """Idempotent upsert into pos.desktop_update_releases.

    Body: see :class:`DesktopReleaseCreate`. Idempotent on
    `(version, channel, platform)` — re-calls update the row in place
    without minting a new release_id.

    Rate-limited to 10 req/min — service accounts call this once per
    release; a flood means the bearer leaked.
    """
    _ = request
    return upsert_release(session, payload)
