"""Inventory API endpoints — stock levels, movements, valuation, and adjustments.

All endpoints require the ``inventory:read`` (or ``inventory:write``) permission
and the ``inventory_management`` plan feature flag.  Only available when
``feature_platform`` is enabled in settings.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from pydantic import BaseModel, Field

from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_tenant_plan_limits
from datapulse.api.limiter import limiter
from datapulse.billing.plans import PlanLimits
from datapulse.inventory.models import (
    AdjustmentRequest,
    InventoryCount,
    InventoryFilter,
    ReorderAlert,
    StockLevel,
    StockMovement,
    StockReconciliation,
    StockValuation,
)
from datapulse.inventory.service import InventoryService
from datapulse.rbac.dependencies import require_permission

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Query parameter model
# ------------------------------------------------------------------


class InventoryQueryParams(BaseModel):
    """Common query parameters shared across inventory endpoints."""

    site_key: int | None = None
    drug_code: Annotated[str | None, Field(max_length=100)] = None
    movement_type: Annotated[str | None, Field(max_length=50)] = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(default=50, ge=1, le=500)


def _to_filter(params: InventoryQueryParams) -> InventoryFilter:
    return InventoryFilter(
        site_key=params.site_key,
        drug_code=params.drug_code,
        movement_type=params.movement_type,
        start_date=params.start_date,
        end_date=params.end_date,
        limit=params.limit,
    )


def _check_inventory_plan(limits: PlanLimits) -> None:
    if not limits.inventory_management:
        raise HTTPException(
            status_code=403,
            detail="Inventory management requires Pro plan or above",
        )


# Dependency type aliases
from datapulse.api.deps import get_inventory_service  # noqa: E402 (avoids circular at module level)

ServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
PlanDep = Annotated[PlanLimits, Depends(get_tenant_plan_limits)]


# ------------------------------------------------------------------
# 1. GET /inventory/stock-levels
# ------------------------------------------------------------------


@router.get("/stock-levels", response_model=list[StockLevel])
@limiter.limit("100/minute")
def get_stock_levels(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockLevel]:
    """Return current stock levels, optionally filtered by site or drug."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 300)
    return service.get_stock_levels(_to_filter(params))


# ------------------------------------------------------------------
# 2. GET /inventory/stock-levels/{drug_code}
# ------------------------------------------------------------------


@router.get("/stock-levels/{drug_code}", response_model=list[StockLevel])
@limiter.limit("100/minute")
def get_stock_level_detail(
    request: Request,
    response: Response,
    drug_code: Annotated[str, Path(max_length=100)],
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockLevel]:
    """Return stock levels for a specific drug across all sites."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 300)
    return service.get_stock_level_detail(drug_code, _to_filter(params))


# ------------------------------------------------------------------
# 3. GET /inventory/movements
# ------------------------------------------------------------------


@router.get("/movements", response_model=list[StockMovement])
@limiter.limit("60/minute")
def get_movements(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockMovement]:
    """Return stock movement events filtered by site, drug, type, or date range."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 120)
    return service.get_movements(_to_filter(params))


# ------------------------------------------------------------------
# 4. GET /inventory/movements/{drug_code}
# ------------------------------------------------------------------


@router.get("/movements/{drug_code}", response_model=list[StockMovement])
@limiter.limit("60/minute")
def get_movements_by_drug(
    request: Request,
    response: Response,
    drug_code: Annotated[str, Path(max_length=100)],
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockMovement]:
    """Return all movement events for a specific drug."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 120)
    return service.get_movements_by_drug(drug_code, _to_filter(params))


# ------------------------------------------------------------------
# 5. GET /inventory/valuation
# ------------------------------------------------------------------


@router.get("/valuation", response_model=list[StockValuation])
@limiter.limit("60/minute")
def get_valuation(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockValuation]:
    """Return stock valuation (weighted average cost) per product/site."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 300)
    return service.get_valuation(_to_filter(params))


# ------------------------------------------------------------------
# 6. GET /inventory/valuation/{drug_code}
# ------------------------------------------------------------------


@router.get("/valuation/{drug_code}", response_model=list[StockValuation])
@limiter.limit("60/minute")
def get_valuation_by_drug(
    request: Request,
    response: Response,
    drug_code: Annotated[str, Path(max_length=100)],
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockValuation]:
    """Return valuation for a specific drug across all sites."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 300)
    return service.get_valuation_by_drug(drug_code, _to_filter(params))


# ------------------------------------------------------------------
# 7. GET /inventory/alerts/reorder
# ------------------------------------------------------------------


@router.get("/alerts/reorder", response_model=list[ReorderAlert])
@limiter.limit("60/minute")
def get_reorder_alerts(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[ReorderAlert]:
    """Return products whose stock has fallen at or below the reorder point."""
    _check_inventory_plan(limits)
    if not limits.stock_alerts:
        raise HTTPException(
            status_code=403,
            detail="Stock alerts require Pro plan or above",
        )
    set_cache_headers(response, 60)
    return service.get_reorder_alerts(_to_filter(params))


# ------------------------------------------------------------------
# 8. POST /inventory/adjustments
# ------------------------------------------------------------------


@router.post("/adjustments", status_code=201)
@limiter.limit("30/minute")
def create_adjustment(
    request: Request,
    body: AdjustmentRequest,
    service: ServiceDep,
    limits: PlanDep,
    user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("inventory:write"))],
) -> dict:
    """Create a manual stock adjustment (damage, shrinkage, correction, etc.)."""
    _check_inventory_plan(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    service.create_adjustment(tenant_id, body)
    return {"status": "created"}


# ------------------------------------------------------------------
# 9. GET /inventory/counts
# ------------------------------------------------------------------


@router.get("/counts", response_model=list[InventoryCount])
@limiter.limit("60/minute")
def get_counts(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[InventoryCount]:
    """Return physical inventory count records."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 300)
    return service.get_counts(_to_filter(params))


# ------------------------------------------------------------------
# 10. GET /inventory/reconciliation
# ------------------------------------------------------------------


@router.get("/reconciliation", response_model=list[StockReconciliation])
@limiter.limit("30/minute")
def get_reconciliation(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockReconciliation]:
    """Return reconciliation report: physical counts vs calculated stock levels."""
    _check_inventory_plan(limits)
    set_cache_headers(response, 300)
    return service.get_reconciliation(_to_filter(params))
