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
from datapulse.onboarding.models import (
    CompleteStepRequest,
    OnboardingStatus,
    SampleLoadResult,
)
from datapulse.onboarding.repository import OnboardingRepository
from datapulse.onboarding.sample_service import SampleLoadService
from datapulse.onboarding.service import OnboardingService
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService

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


def get_sample_load_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> SampleLoadService:
    pipeline_service = PipelineService(PipelineRepository(session))
    quality_repo = QualityRepository(session)
    return SampleLoadService(
        session=session,
        pipeline_service=pipeline_service,
        quality_repo=quality_repo,
    )


ServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]
SampleLoadDep = Annotated[SampleLoadService, Depends(get_sample_load_service)]


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


@router.post("/load-sample", response_model=SampleLoadResult)
@limiter.limit("5/minute")
def load_sample_dataset(
    request: Request,
    sample_service: SampleLoadDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> SampleLoadResult:
    """Load the curated pharma sample dataset for the current tenant.

    Idempotent: subsequent calls clear the prior sample rows before
    inserting a fresh batch. Returns `rows_loaded`, `pipeline_run_id`,
    and `duration_seconds`. Intended for the onboarding wizard's
    "Use sample pharma data" CTA (Phase 2 Task 1 / #400).
    """
    tenant_id = user.get("tenant_id", 1)
    user_id = user.get("sub", user.get("user_id", "anonymous"))
    return sample_service.load(tenant_id=tenant_id, user_id=user_id)
