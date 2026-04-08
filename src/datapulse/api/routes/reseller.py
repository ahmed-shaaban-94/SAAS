"""Reseller management API endpoints.

Provides reseller CRUD, dashboard, tenants, commissions, and payouts
under ``/reseller/``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.reseller.models import (
    CommissionResponse,
    PayoutResponse,
    ResellerCreate,
    ResellerDashboard,
    ResellerResponse,
    ResellerTenantResponse,
)
from datapulse.reseller.repository import ResellerRepository
from datapulse.reseller.service import ResellerService

router = APIRouter(
    prefix="/reseller",
    tags=["reseller"],
    dependencies=[Depends(get_current_user)],
)


def get_reseller_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ResellerService:
    repo = ResellerRepository(session)
    return ResellerService(repo)


ServiceDep = Annotated[ResellerService, Depends(get_reseller_service)]


def _set_cache(response: Response, max_age: int) -> None:
    response.headers["Cache-Control"] = f"max-age={max_age}, private"


@router.get("/", response_model=list[ResellerResponse])
@limiter.limit("60/minute")
def list_resellers(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[ResellerResponse]:
    """List all resellers."""
    _set_cache(response, 120)
    return service.list_resellers()


@router.post("/", response_model=ResellerResponse, status_code=201)
@limiter.limit("5/minute")
def create_reseller(
    request: Request,
    data: ResellerCreate,
    service: ServiceDep,
) -> ResellerResponse:
    """Create a new reseller partner."""
    return service.create_reseller(data)


@router.get("/{reseller_id}/dashboard", response_model=ResellerDashboard)
@limiter.limit("60/minute")
def get_dashboard(
    request: Request,
    response: Response,
    reseller_id: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> ResellerDashboard:
    """Get reseller dashboard overview."""
    _set_cache(response, 60)
    try:
        return service.get_dashboard(reseller_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{reseller_id}/tenants", response_model=list[ResellerTenantResponse])
@limiter.limit("60/minute")
def get_tenants(
    request: Request,
    response: Response,
    reseller_id: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> list[ResellerTenantResponse]:
    """Get tenants under a reseller."""
    _set_cache(response, 120)
    return service.get_tenants(reseller_id)


@router.get("/{reseller_id}/commissions", response_model=list[CommissionResponse])
@limiter.limit("60/minute")
def get_commissions(
    request: Request,
    response: Response,
    reseller_id: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> list[CommissionResponse]:
    """Get commission history for a reseller."""
    _set_cache(response, 120)
    return service.get_commissions(reseller_id)


@router.get("/{reseller_id}/payouts", response_model=list[PayoutResponse])
@limiter.limit("60/minute")
def get_payouts(
    request: Request,
    response: Response,
    reseller_id: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> list[PayoutResponse]:
    """Get payout history for a reseller."""
    _set_cache(response, 120)
    return service.get_payouts(reseller_id)
