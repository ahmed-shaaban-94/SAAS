"""Control Center — sync job trigger and history endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.api.routes.control_center._deps import ServiceDep
from datapulse.control_center.models import (
    SyncJob,
    SyncJobList,
    TriggerSyncRequest,
)
from datapulse.rbac.dependencies import require_permission

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter()


# ------------------------------------------------------------------
# Sync history — view (connection-scoped)
# ------------------------------------------------------------------


@router.get(
    "/connections/{connection_id}/sync-history",
    response_model=SyncJobList,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def list_sync_history(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SyncJobList:
    """List past sync jobs for a source connection (joined with pipeline_runs)."""
    # Verify connection exists & is tenant-visible (RLS enforces scope)
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return service.list_sync_history(connection_id=connection_id, page=page, page_size=page_size)


# ------------------------------------------------------------------
# Sync — trigger (Phase 1e)
# ------------------------------------------------------------------


@router.post(
    "/connections/{connection_id}/sync",
    response_model=SyncJob,
    status_code=202,
    dependencies=[Depends(require_permission("control_center:sync:run"))],
)
@limiter.limit("10/minute")
def trigger_sync(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    connection_id: Annotated[int, Path(ge=1)],
    body: TriggerSyncRequest,
) -> SyncJob:
    """Trigger a manual sync for the given source connection.

    Creates a ``sync_jobs`` row (and a UUID run id) so the result can be
    tracked via ``GET /connections/{id}/sync-history``.
    """
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    try:
        return service.trigger_sync(
            connection_id,
            tenant_id=tenant_id,
            run_mode=body.run_mode,
            release_id=body.release_id,
            profile_id=body.profile_id,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
