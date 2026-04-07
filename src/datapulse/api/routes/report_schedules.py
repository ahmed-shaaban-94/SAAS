"""Report schedule API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.reports.schedule_models import (
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleUpdate,
)
from datapulse.reports.schedule_repository import ScheduleRepository

router = APIRouter(
    prefix="/report-schedules",
    tags=["report-schedules"],
    dependencies=[Depends(get_current_user)],
)


def _get_repo(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ScheduleRepository:
    return ScheduleRepository(session)


RepoDep = Annotated[ScheduleRepository, Depends(_get_repo)]


@router.get("", response_model=list[ReportScheduleResponse])
@limiter.limit("30/minute")
def list_schedules(request: Request, repo: RepoDep) -> list[ReportScheduleResponse]:
    return repo.list_schedules()


@router.post("", response_model=ReportScheduleResponse, status_code=201)
@limiter.limit("5/minute")
def create_schedule(
    request: Request, repo: RepoDep, body: ReportScheduleCreate
) -> ReportScheduleResponse:
    return repo.create_schedule(body)


@router.patch("/{schedule_id}", response_model=ReportScheduleResponse)
@limiter.limit("5/minute")
def update_schedule(
    request: Request,
    repo: RepoDep,
    body: ReportScheduleUpdate,
    schedule_id: int = Path(),
) -> ReportScheduleResponse:
    result = repo.update_schedule(schedule_id, body)
    if not result:
        raise HTTPException(404, "Schedule not found")
    return result


@router.delete("/{schedule_id}", status_code=204)
@limiter.limit("5/minute")
def delete_schedule(request: Request, repo: RepoDep, schedule_id: int = Path()) -> None:
    if not repo.delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")
