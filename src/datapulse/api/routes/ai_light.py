"""AI-Light API endpoints.

Provides 4 endpoints under ``/ai-light/`` for AI-powered insights:
- GET /status — check if OpenRouter is configured
- GET /summary — executive narrative summary
- GET /anomalies — anomaly detection report
- GET /changes — change narrative between two periods
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from datapulse.ai_light.models import AISummary, AnomalyReport, ChangeNarrative
from datapulse.ai_light.service import AILightService
from datapulse.api.limiter import limiter
from datapulse.api.deps import get_ai_light_service, verify_api_key
from datapulse.logging import get_logger

router = APIRouter(prefix="/ai-light", tags=["ai-light"], dependencies=[Depends(verify_api_key)])
log = get_logger(__name__)

ServiceDep = Annotated[AILightService, Depends(get_ai_light_service)]


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
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")


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
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")


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
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")
