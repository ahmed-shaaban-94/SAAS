"""Audit log API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_audit_service
from datapulse.api.limiter import limiter
from datapulse.audit.models import AuditLogPage
from datapulse.audit.service import AuditService

router = APIRouter(
    prefix="/audit-log",
    tags=["audit"],
    dependencies=[Depends(get_current_user)],
)


ServiceDep = Annotated[AuditService, Depends(get_audit_service)]


@router.get("", response_model=AuditLogPage)
@limiter.limit("30/minute")
def list_audit_log(
    request: Request,
    service: ServiceDep,
    action: str | None = Query(None),
    endpoint: str | None = Query(None),
    method: str | None = Query(None),
    user_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> AuditLogPage:
    return service.list_entries(
        action=action,
        endpoint=endpoint,
        method=method,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
