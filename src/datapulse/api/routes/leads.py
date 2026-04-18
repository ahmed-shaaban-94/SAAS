"""Lead capture API route — public, no auth required."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from datapulse.api.deps import get_plain_session
from datapulse.api.limiter import limiter
from datapulse.leads.models import LeadRequest, LeadResponse
from datapulse.leads.repository import LeadRepository
from datapulse.leads.service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


def get_lead_service(
    session: Annotated[Session, Depends(get_plain_session)],
) -> LeadService:
    return LeadService(LeadRepository(session))


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
