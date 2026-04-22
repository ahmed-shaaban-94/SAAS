"""Anomaly detection API endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from datapulse.anomalies.models import AnomalyAlertResponse, AnomalyCard
from datapulse.anomalies.service import AnomalyService
from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_anomaly_service
from datapulse.api.limiter import limiter

router = APIRouter(
    prefix="/anomalies",
    tags=["anomalies"],
    dependencies=[Depends(get_current_user)],
)


_ServiceDep = Annotated[AnomalyService, Depends(get_anomaly_service)]


@router.get("/active", response_model=list[AnomalyAlertResponse])
@limiter.limit("60/minute")
def get_active_alerts(
    request: Request,
    response: Response,
    service: _ServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[AnomalyAlertResponse]:
    """Return unacknowledged, unsuppressed anomaly alerts."""
    set_cache_headers(response, 60)
    return service.get_active_alerts(limit=limit)


@router.get("/cards", response_model=list[AnomalyCard])
@limiter.limit("60/minute")
def get_active_cards(
    request: Request,
    response: Response,
    service: _ServiceDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[AnomalyCard]:
    """Return active anomalies projected onto the design-facing card shape.

    Powers the new dashboard anomaly-feed widget — kind/title/body/time_ago/
    confidence are pre-computed server-side so the frontend renders without
    transformation (#508). Backward-compatible with ``/anomalies/active``.
    """
    set_cache_headers(response, 60)
    return service.get_active_cards(limit=limit)


@router.get("/history", response_model=list[AnomalyAlertResponse])
@limiter.limit("60/minute")
def get_alert_history(
    request: Request,
    response: Response,
    service: _ServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AnomalyAlertResponse]:
    """Return anomaly alert history with optional date range filter."""
    set_cache_headers(response, 120)
    return service.get_history(start_date, end_date, limit)


@router.post("/{alert_id}/acknowledge")
@limiter.limit("30/minute")
def acknowledge_alert(
    request: Request,
    service: _ServiceDep,
    alert_id: Annotated[int, Path(ge=1)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Acknowledge an anomaly alert."""
    username = user.get("email", user.get("sub", "unknown"))
    success = service.acknowledge(alert_id, username)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
    return {"acknowledged": True, "alert_id": alert_id}
