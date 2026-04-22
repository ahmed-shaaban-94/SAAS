"""Reseller management API endpoints.

Provides reseller CRUD, dashboard, tenants, commissions, and payouts
under ``/reseller/``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_reseller_service
from datapulse.api.limiter import limiter
from datapulse.reseller.models import (
    CommissionResponse,
    PayoutResponse,
    ResellerCreate,
    ResellerDashboard,
    ResellerResponse,
    ResellerTenantResponse,
)
from datapulse.reseller.service import ResellerService

router = APIRouter(
    prefix="/reseller",
    tags=["reseller"],
    dependencies=[Depends(get_current_user)],
)


ServiceDep = Annotated[ResellerService, Depends(get_reseller_service)]
CurrentUserDep = Annotated[dict[str, Any], Depends(get_current_user)]

_PLATFORM_ADMIN_ROLES = frozenset({"admin", "owner"})


def _check_reseller_access(
    reseller_id: int,
    user: dict[str, Any],
    service: ResellerService,
) -> None:
    """Raise 403 unless the caller's tenant is associated with this reseller.

    Platform admins (roles: admin/owner) bypass the ownership check.
    """
    roles: list[str] = user.get("roles", [])
    if _PLATFORM_ADMIN_ROLES.intersection(roles):
        return
    tenant_id = int(user.get("tenant_id", "0"))
    if not service.tenant_belongs_to_reseller(tenant_id, reseller_id):
        raise HTTPException(status_code=403, detail="Access denied to this reseller")


@router.get("/", response_model=list[ResellerResponse])
@limiter.limit("60/minute")
def list_resellers(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[ResellerResponse]:
    """List all resellers."""
    set_cache_headers(response, 120)
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
    service: ServiceDep,
    user: CurrentUserDep,
    reseller_id: int = Path(..., gt=0),
) -> ResellerDashboard:
    """Get reseller dashboard overview."""
    _check_reseller_access(reseller_id, user, service)
    set_cache_headers(response, 60)
    try:
        return service.get_dashboard(reseller_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{reseller_id}/tenants", response_model=list[ResellerTenantResponse])
@limiter.limit("60/minute")
def get_tenants(
    request: Request,
    response: Response,
    service: ServiceDep,
    user: CurrentUserDep,
    reseller_id: int = Path(..., gt=0),
) -> list[ResellerTenantResponse]:
    """Get tenants under a reseller."""
    _check_reseller_access(reseller_id, user, service)
    set_cache_headers(response, 120)
    return service.get_tenants(reseller_id)


@router.get("/{reseller_id}/commissions", response_model=list[CommissionResponse])
@limiter.limit("60/minute")
def get_commissions(
    request: Request,
    response: Response,
    service: ServiceDep,
    user: CurrentUserDep,
    reseller_id: int = Path(..., gt=0),
) -> list[CommissionResponse]:
    """Get commission history for a reseller."""
    _check_reseller_access(reseller_id, user, service)
    set_cache_headers(response, 120)
    return service.get_commissions(reseller_id)


@router.get("/{reseller_id}/payouts", response_model=list[PayoutResponse])
@limiter.limit("60/minute")
def get_payouts(
    request: Request,
    response: Response,
    service: ServiceDep,
    user: CurrentUserDep,
    reseller_id: int = Path(..., gt=0),
) -> list[PayoutResponse]:
    """Get payout history for a reseller."""
    _check_reseller_access(reseller_id, user, service)
    set_cache_headers(response, 120)
    return service.get_payouts(reseller_id)
