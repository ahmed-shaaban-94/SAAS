"""Targets & alerts API endpoints.

Provides target CRUD, target-vs-actual summaries, alert configuration
management, and alert log operations under ``/targets/`` and ``/alerts/``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.targets.models import (
    AlertConfigCreate,
    AlertConfigResponse,
    AlertLogResponse,
    TargetCreate,
    TargetResponse,
    TargetSummary,
)
from datapulse.targets.repository import TargetsRepository
from datapulse.targets.service import TargetsService

router = APIRouter(
    prefix="/targets",
    tags=["targets"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Dependency injection (local factory — does not modify deps.py)
# ------------------------------------------------------------------


def get_targets_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> TargetsService:
    repo = TargetsRepository(session)
    return TargetsService(repo)


ServiceDep = Annotated[TargetsService, Depends(get_targets_service)]


# ------------------------------------------------------------------
# Cache-Control helper
# ------------------------------------------------------------------


def _set_cache(response: Response, max_age: int) -> None:
    """Set Cache-Control header for browser caching (always private for RLS)."""
    response.headers["Cache-Control"] = f"max-age={max_age}, private"


# ------------------------------------------------------------------
# Target endpoints
# ------------------------------------------------------------------


@router.post("/", response_model=TargetResponse, status_code=201)
@limiter.limit("5/minute")
def create_target(
    request: Request,
    data: TargetCreate,
    service: ServiceDep,
) -> TargetResponse:
    """Create a new sales target."""
    return service.create_target(data)


@router.get("/", response_model=list[TargetResponse])
@limiter.limit("60/minute")
def list_targets(
    request: Request,
    response: Response,
    service: ServiceDep,
    target_type: Annotated[str | None, Query(max_length=50)] = None,
    granularity: Annotated[str | None, Query(max_length=20)] = None,
    period: Annotated[str | None, Query(max_length=10)] = None,
) -> list[TargetResponse]:
    """List sales targets with optional filters."""
    _set_cache(response, 60)
    return service.list_targets(
        target_type=target_type,
        granularity=granularity,
        period=period,
    )


@router.delete("/{target_id}", status_code=204)
@limiter.limit("5/minute")
def delete_target(
    request: Request,
    target_id: Annotated[int, Path(ge=1, description="Target ID")],
    service: ServiceDep,
) -> None:
    """Delete a sales target by ID."""
    deleted = service.delete_target(target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Target not found")


@router.get("/summary", response_model=TargetSummary)
@limiter.limit("60/minute")
def get_target_summary(
    request: Request,
    response: Response,
    service: ServiceDep,
    year: Annotated[int, Query(ge=2020, le=2100, description="Year for summary")] = 2025,
) -> TargetSummary:
    """Target vs actual revenue summary for a given year."""
    _set_cache(response, 120)
    return service.get_target_summary(year)


# ------------------------------------------------------------------
# Alert config endpoints
# ------------------------------------------------------------------


@router.get("/alerts/configs", response_model=list[AlertConfigResponse])
@limiter.limit("60/minute")
def list_alert_configs(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[AlertConfigResponse]:
    """List all alert configurations."""
    _set_cache(response, 60)
    return service.list_alert_configs()


@router.post("/alerts/configs", response_model=AlertConfigResponse, status_code=201)
@limiter.limit("5/minute")
def create_alert_config(
    request: Request,
    data: AlertConfigCreate,
    service: ServiceDep,
) -> AlertConfigResponse:
    """Create a new alert configuration."""
    return service.create_alert_config(data)


@router.patch("/alerts/configs/{alert_id}", response_model=AlertConfigResponse)
@limiter.limit("5/minute")
def toggle_alert_config(
    request: Request,
    alert_id: Annotated[int, Path(ge=1, description="Alert config ID")],
    service: ServiceDep,
    enabled: Annotated[bool, Query(description="Enable or disable the alert")] = True,
) -> AlertConfigResponse:
    """Enable or disable an alert configuration."""
    result = service.toggle_alert(alert_id, enabled)
    if result is None:
        raise HTTPException(status_code=404, detail="Alert config not found")
    return result


# ------------------------------------------------------------------
# Alert log endpoints
# ------------------------------------------------------------------


@router.get("/alerts/log", response_model=list[AlertLogResponse])
@limiter.limit("60/minute")
def get_alert_logs(
    request: Request,
    response: Response,
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    unacknowledged_only: bool = False,
) -> list[AlertLogResponse]:
    """Get alert history log."""
    _set_cache(response, 30)
    return service.get_active_alerts(
        limit=limit,
        unacknowledged_only=unacknowledged_only,
    )


@router.post("/alerts/log/{alert_id}/acknowledge", status_code=200)
@limiter.limit("5/minute")
def acknowledge_alert(
    request: Request,
    alert_id: Annotated[int, Path(ge=1, description="Alert log ID")],
    service: ServiceDep,
) -> dict[str, bool]:
    """Acknowledge an alert log entry."""
    acknowledged = service.acknowledge_alert(alert_id)
    if not acknowledged:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or already acknowledged",
        )
    return {"acknowledged": True}
