"""Lead capture API route — public, no auth required."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from datapulse.api.deps import get_lead_service
from datapulse.api.limiter import limiter
from datapulse.leads.models import LeadRequest, LeadResponse
from datapulse.leads.service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


LeadServiceDep = Annotated[LeadService, Depends(get_lead_service)]


@router.post("", response_model=LeadResponse)
@limiter.limit("5/minute")
async def capture_lead(
    request: Request,
    data: LeadRequest,
    service: LeadServiceDep,
) -> LeadResponse:
    """Record a pilot access / waitlist request. Public endpoint — no auth."""
    return service.capture(data)
