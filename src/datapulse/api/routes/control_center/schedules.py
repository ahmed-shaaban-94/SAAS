"""Control Center — sync schedule endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.api.routes.control_center._deps import ServiceDep
from datapulse.control_center.models import (
    CreateScheduleRequest,
    SyncSchedule,
    SyncScheduleList,
)
from datapulse.rbac.dependencies import require_permission

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter()


# ------------------------------------------------------------------
# Sync schedules — Phase 2
# ------------------------------------------------------------------


@router.post(
    "/connections/{connection_id}/schedule",
    response_model=SyncSchedule,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:sync:schedule"))],
)
@limiter.limit("10/minute")
def create_schedule(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    connection_id: Annotated[int, Path(ge=1)],
    body: CreateScheduleRequest,
) -> SyncSchedule:
    """Create a cron schedule that will auto-trigger syncs for the connection.

    ``cron_expr`` must be a 5-field UNIX cron expression (e.g. ``'0 6 * * *'``).
    APScheduler picks up new schedules on next startup; to apply immediately
    you can restart the scheduler or call the internal reload endpoint.
    """
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    try:
        return service.create_schedule(
            connection_id=connection_id,
            tenant_id=tenant_id,
            cron_expr=body.cron_expr,
            is_active=body.is_active,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/connections/{connection_id}/schedules",
    response_model=SyncScheduleList,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def list_schedules(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SyncScheduleList:
    """List cron schedules for a source connection."""
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return service.list_schedules(connection_id=connection_id, page=page, page_size=page_size)


@router.delete(
    "/connections/{connection_id}/schedule/{schedule_id}",
    status_code=204,
    dependencies=[Depends(require_permission("control_center:sync:schedule"))],
)
@limiter.limit("10/minute")
def delete_schedule(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    schedule_id: Annotated[int, Path(ge=1)],
) -> None:
    """Delete a cron schedule permanently.

    The schedule is removed immediately; the APScheduler job will be
    deregistered on next scheduler reload.
    """
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    found = service.delete_schedule(schedule_id)
    if not found:
        raise HTTPException(status_code=404, detail="schedule_not_found")
