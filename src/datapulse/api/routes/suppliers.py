"""Suppliers API endpoints.

Provides 5 supplier directory + performance endpoints.
All endpoints are gated by the purchase_orders plan feature flag.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_supplier_service, get_tenant_plan_limits
from datapulse.billing.plans import PlanLimits
from datapulse.rbac.dependencies import require_permission
from datapulse.suppliers.models import (
    SupplierCreateRequest,
    SupplierInfo,
    SupplierList,
    SupplierPerformance,
    SupplierUpdateRequest,
)
from datapulse.suppliers.service import SuppliersService

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(get_current_user)],
)

SupplierServiceDep = Annotated[SuppliersService, Depends(get_supplier_service)]
LimitsDep = Annotated[PlanLimits, Depends(get_tenant_plan_limits)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _check_suppliers_feature(limits: PlanLimits) -> None:
    if not limits.purchase_orders:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "feature_not_available",
                "feature": "suppliers",
                "message": "Supplier management is not available on your current plan. "
                "Upgrade to Pro or Enterprise to enable this feature.",
            },
        )


# ── GET /suppliers ────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=SupplierList,
    dependencies=[Depends(require_permission("suppliers:read"))],
)
def list_suppliers(
    service: SupplierServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SupplierList:
    """List all suppliers with optional active filter."""
    _check_suppliers_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.list_suppliers(
        tenant_id=tenant_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )


# ── POST /suppliers ───────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=SupplierInfo,
    status_code=201,
    dependencies=[Depends(require_permission("suppliers:write"))],
)
def create_supplier(
    service: SupplierServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    body: SupplierCreateRequest,
) -> SupplierInfo:
    """Create a new supplier in the directory."""
    _check_suppliers_feature(limits)

    # Enforce max_suppliers plan limit
    if limits.max_suppliers == 0:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "feature_not_available",
                "feature": "suppliers",
                "message": "Supplier management is not available on your current plan.",
            },
        )

    tenant_id = int(user.get("tenant_id", "1"))
    return service.create_supplier(body, tenant_id)


# ── GET /suppliers/{supplier_code} ────────────────────────────────────────────


@router.get(
    "/{supplier_code}",
    response_model=SupplierInfo,
    dependencies=[Depends(require_permission("suppliers:read"))],
)
def get_supplier(
    service: SupplierServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    supplier_code: str,
) -> SupplierInfo:
    """Get a single supplier by code."""
    _check_suppliers_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.get_supplier(supplier_code, tenant_id)


# ── PUT /suppliers/{supplier_code} ────────────────────────────────────────────


@router.put(
    "/{supplier_code}",
    response_model=SupplierInfo,
    dependencies=[Depends(require_permission("suppliers:write"))],
)
def update_supplier(
    service: SupplierServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    supplier_code: str,
    body: SupplierUpdateRequest,
) -> SupplierInfo:
    """Update supplier contact info and settings."""
    _check_suppliers_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.update_supplier(supplier_code, tenant_id, body)


# ── GET /suppliers/{supplier_code}/performance ────────────────────────────────


@router.get(
    "/{supplier_code}/performance",
    response_model=SupplierPerformance,
    dependencies=[Depends(require_permission("suppliers:read"))],
)
def get_supplier_performance(
    service: SupplierServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    supplier_code: str,
) -> SupplierPerformance:
    """Get supplier performance metrics (lead time, fill rate, spend)."""
    _check_suppliers_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.get_performance(supplier_code, tenant_id)
