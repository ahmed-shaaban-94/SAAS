"""Notification center API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import StreamingResponse

from datapulse.api.auth import get_current_user
from datapulse.api.deps import CurrentUser, get_notification_service
from datapulse.api.limiter import limiter
from datapulse.notifications_center.models import NotificationCount, NotificationResponse
from datapulse.notifications_center.service import NotificationService
from datapulse.notifications_center.streaming import iter_unread_count_events

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
)


ServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("", response_model=list[NotificationResponse])
@limiter.limit("30/minute")
def list_notifications(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
):
    return service.list_notifications(user["sub"], unread_only, limit)


@router.get("/count", response_model=NotificationCount)
@limiter.limit("60/minute")
def unread_count(request: Request, service: ServiceDep, user: CurrentUser):
    return service.unread_count(user["sub"])


@router.post("/{notification_id}/read", status_code=204)
@limiter.limit("30/minute")
def mark_read(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    notification_id: int = Path(),
):
    service.mark_read(notification_id, user["sub"])


@router.post("/read-all", status_code=204)
@limiter.limit("10/minute")
def mark_all_read(request: Request, service: ServiceDep, user: CurrentUser):
    service.mark_all_read(user["sub"])


@router.get("/stream")
async def notification_stream(
    request: Request,
    user: Annotated[dict, Depends(get_current_user)],
):
    """SSE stream for real-time notification count updates."""
    user_id = user["sub"]
    tenant_id = user.get("tenant_id", "1")

    return StreamingResponse(
        iter_unread_count_events(user_id, tenant_id, request.is_disconnected),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
