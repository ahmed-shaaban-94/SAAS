"""Onboarding wizard API endpoints.

Provides onboarding status retrieval, step completion, and skip
functionality under ``/onboarding/``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.onboarding.models import CompleteStepRequest, OnboardingStatus
from datapulse.onboarding.repository import OnboardingRepository
from datapulse.onboarding.service import OnboardingService

router = APIRouter(
    prefix="/onboarding",
    tags=["onboarding"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Dependency injection (local factory — does not modify deps.py)
# ------------------------------------------------------------------


def get_onboarding_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> OnboardingService:
    repo = OnboardingRepository(session)
    return OnboardingService(repo)


ServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("/status", response_model=OnboardingStatus)
@limiter.limit("30/minute")
def get_onboarding_status(
    request: Request,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> OnboardingStatus:
    """Return the current onboarding status for the authenticated user."""
    tenant_id = user.get("tenant_id", 1)
    user_id = user.get("sub", user.get("user_id", "anonymous"))
    return service.get_status(tenant_id=tenant_id, user_id=user_id)


@router.post("/complete-step", response_model=OnboardingStatus)
@limiter.limit("10/minute")
def complete_step(
    request: Request,
    data: CompleteStepRequest,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> OnboardingStatus:
    """Mark a single onboarding step as completed."""
    tenant_id = user.get("tenant_id", 1)
    user_id = user.get("sub", user.get("user_id", "anonymous"))
    return service.complete_step(
        tenant_id=tenant_id,
        user_id=user_id,
        step=data.step,
    )


@router.post("/skip", response_model=OnboardingStatus)
@limiter.limit("10/minute")
def skip_onboarding(
    request: Request,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> OnboardingStatus:
    """Skip the onboarding wizard entirely."""
    tenant_id = user.get("tenant_id", 1)
    user_id = user.get("sub", user.get("user_id", "anonymous"))
    return service.skip(tenant_id=tenant_id, user_id=user_id)
