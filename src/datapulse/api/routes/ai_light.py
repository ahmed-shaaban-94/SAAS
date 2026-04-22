"""AI-Light API endpoints.

Provides 5 endpoints under ``/ai-light/`` for AI-powered insights:
- GET /status — check if OpenRouter is configured
- GET /summary — executive narrative summary
- GET /anomalies — anomaly detection report
- GET /changes — change narrative between two periods
- GET /top-insight — single actionable insight for the banner (#510)
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from datapulse.ai_light.models import AISummary, AnomalyReport, ChangeNarrative, TopInsight
from datapulse.ai_light.service import AILightService
from datapulse.ai_light.top_insight import anomaly_to_top_insight, pick_top_anomaly
from datapulse.anomalies.service import AnomalyService
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_ai_light_service, get_anomaly_service
from datapulse.api.limiter import limiter
from datapulse.logging import get_logger
from datapulse.rbac.dependencies import require_permission

router = APIRouter(
    prefix="/ai-light",
    tags=["ai-light"],
    dependencies=[Depends(require_permission("insights:view"))],
)
log = get_logger(__name__)

ServiceDep = Annotated[AILightService, Depends(get_ai_light_service)]
AnomalyServiceDep = Annotated[AnomalyService, Depends(get_anomaly_service)]


@router.get("/status")
@limiter.limit("20/minute")
def get_status(request: Request, service: ServiceDep) -> dict:
    """Check if AI-Light is available (OpenRouter configured)."""
    return {"available": service.is_available}


@router.get("/summary", response_model=AISummary)
@limiter.limit("20/minute")
def get_summary(
    request: Request,
    service: ServiceDep,
    target_date: Annotated[date | None, Query()] = None,
) -> AISummary:
    """Generate an AI-powered executive summary."""
    if not service.is_available:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")
    try:
        return service.generate_summary(target_date)
    except Exception as exc:
        log.error("ai_summary_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


@router.get("/anomalies", response_model=AnomalyReport)
@limiter.limit("20/minute")
def get_anomalies(
    request: Request,
    service: ServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> AnomalyReport:
    """Detect anomalies in daily sales data."""
    try:
        return service.detect_anomalies(start_date, end_date)
    except Exception as exc:
        log.error("ai_anomalies_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


@router.get("/changes", response_model=ChangeNarrative)
@limiter.limit("20/minute")
def get_changes(
    request: Request,
    service: ServiceDep,
    current_date: Annotated[date | None, Query()] = None,
    previous_date: Annotated[date | None, Query()] = None,
) -> ChangeNarrative:
    """Compare two dates and explain the key changes."""
    try:
        return service.explain_changes(current_date, previous_date)
    except Exception as exc:
        log.error("ai_changes_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


@router.get(
    "/top-insight", response_model=TopInsight, responses={204: {"description": "No active insight"}}
)
@limiter.limit("60/minute")
def get_top_insight(
    request: Request,
    response: Response,
    anomaly_service: AnomalyServiceDep,
) -> TopInsight | Response:
    """Single actionable insight for the dashboard alert banner (#510).

    Picks the highest-severity unsuppressed anomaly and returns a banner-
    ready card with a deep-link CTA. Responds **204 No Content** when
    nothing currently demands attention — the frontend hides the banner
    silently instead of showing a stale or empty insight.

    Lightweight by design: reads directly from the anomaly store (no LLM
    call on the critical-path). The existing ``/summary`` and ``/changes``
    endpoints remain the place for narrative-heavy output.
    """
    set_cache_headers(response, 300)
    alerts = anomaly_service.get_active_alerts(limit=20)

    top = pick_top_anomaly(alerts)
    if top is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return anomaly_to_top_insight(top)
