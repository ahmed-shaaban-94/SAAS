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

from fastapi import APIRouter, Depends, HTTPException, Query

from datapulse.ai_light.models import AISummary, AnomalyReport, ChangeNarrative
from datapulse.ai_light.service import AILightService
from datapulse.api.deps import get_ai_light_service

router = APIRouter(prefix="/ai-light", tags=["ai-light"])

ServiceDep = Annotated[AILightService, Depends(get_ai_light_service)]


@router.get("/status")
def get_status(service: ServiceDep) -> dict:
    """Check if AI-Light is available (OpenRouter configured)."""
    return {"available": service.is_available}


@router.get("/summary", response_model=AISummary)
def get_summary(
    service: ServiceDep,
    target_date: Annotated[date | None, Query()] = None,
) -> AISummary:
    """Generate an AI-powered executive summary."""
    if not service.is_available:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")
    try:
        return service.generate_summary(target_date)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")


@router.get("/anomalies", response_model=AnomalyReport)
def get_anomalies(
    service: ServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> AnomalyReport:
    """Detect anomalies in daily sales data."""
    try:
        return service.detect_anomalies(start_date, end_date)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")


@router.get("/changes", response_model=ChangeNarrative)
def get_changes(
    service: ServiceDep,
    current_date: Annotated[date | None, Query()] = None,
    previous_date: Annotated[date | None, Query()] = None,
) -> ChangeNarrative:
    """Compare two dates and explain the key changes."""
    try:
        return service.explain_changes(current_date, previous_date)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")
