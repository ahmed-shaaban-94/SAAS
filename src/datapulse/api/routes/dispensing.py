"""Dispensing Analytics API endpoints.

All endpoints require the ``dispensing_analytics`` plan feature flag and
``dispensing:read`` RBAC permission. Only available when ``feature_platform``
is enabled in settings.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_tenant_plan_limits
from datapulse.api.limiter import limiter
from datapulse.billing.plans import PlanLimits
from datapulse.dispensing.models import (
    DaysOfStock,
    DispenseRate,
    DispensingFilter,
    StockoutRisk,
    VelocityClassification,
)
from datapulse.dispensing.service import DispensingService
from datapulse.inventory.models import StockReconciliation
from datapulse.rbac.dependencies import require_permission

router = APIRouter(
    prefix="/dispensing",
    tags=["dispensing"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _check_dispensing_plan(limits: PlanLimits) -> None:
    if not limits.dispensing_analytics:
        raise HTTPException(
            status_code=403,
            detail="Dispensing analytics requires Pro plan or above",
        )


from datapulse.api.deps import get_dispensing_service  # noqa: E402

ServiceDep = Annotated[DispensingService, Depends(get_dispensing_service)]
PlanDep = Annotated[PlanLimits, Depends(get_tenant_plan_limits)]


def _make_filter(
    site_key: int | None = None,
    drug_code: str | None = None,
    velocity_class: str | None = None,
    risk_level: str | None = None,
    limit: int = 100,
) -> DispensingFilter:
    return DispensingFilter(
        site_key=site_key,
        drug_code=drug_code,
        velocity_class=velocity_class,
        risk_level=risk_level,
        limit=limit,
    )


# ------------------------------------------------------------------
# 1. GET /dispensing/rates — avg dispense rates per product/site
# ------------------------------------------------------------------


@router.get("/rates", response_model=list[DispenseRate])
@limiter.limit("60/minute")
def get_dispense_rates(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("dispensing:read"))],
    site_key: int | None = None,
    drug_code: str | None = None,
    limit: int = 100,
) -> list[DispenseRate]:
    """Return average daily/weekly/monthly dispense rates per product per site (last 90 days)."""
    _check_dispensing_plan(limits)
    set_cache_headers(response, 300)
    f = _make_filter(site_key=site_key, drug_code=drug_code, limit=limit)
    return service.get_dispense_rates(f)


# ------------------------------------------------------------------
# 2. GET /dispensing/days-of-stock — days of stock per product/site
# ------------------------------------------------------------------


@router.get("/days-of-stock", response_model=list[DaysOfStock])
@limiter.limit("60/minute")
def get_days_of_stock(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("dispensing:read"))],
    site_key: int | None = None,
    drug_code: str | None = None,
    limit: int = 100,
) -> list[DaysOfStock]:
    """Return estimated days of stock remaining per product per site.

    Returns NULL for days_of_stock when no recent dispense history exists.
    """
    _check_dispensing_plan(limits)
    set_cache_headers(response, 300)
    f = _make_filter(site_key=site_key, drug_code=drug_code, limit=limit)
    return service.get_days_of_stock(f)


# ------------------------------------------------------------------
# 3. GET /dispensing/velocity — product velocity classification
# ------------------------------------------------------------------


@router.get("/velocity", response_model=list[VelocityClassification])
@limiter.limit("60/minute")
def get_product_velocity(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("dispensing:read"))],
    drug_code: str | None = None,
    velocity_class: str | None = None,
    limit: int = 100,
) -> list[VelocityClassification]:
    """Return product velocity classification (fast_mover / normal_mover / slow_mover / dead_stock).

    Classification is relative to the category average dispense rate.
    """
    _check_dispensing_plan(limits)
    set_cache_headers(response, 600)
    return service.get_velocity(
        _make_filter(drug_code=drug_code, velocity_class=velocity_class, limit=limit)
    )


# ------------------------------------------------------------------
# 4. GET /dispensing/stockout-risk — products at risk of stockout
# ------------------------------------------------------------------


@router.get("/stockout-risk", response_model=list[StockoutRisk])
@limiter.limit("60/minute")
def get_stockout_risk(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("dispensing:read"))],
    site_key: int | None = None,
    drug_code: str | None = None,
    risk_level: str | None = None,
    limit: int = 100,
) -> list[StockoutRisk]:
    """Return products where days_of_stock < reorder_lead_days or stock <= reorder_point.

    Risk levels: stockout (qty <= 0), critical (days < lead_days), at_risk (qty <= reorder_point).
    """
    _check_dispensing_plan(limits)
    set_cache_headers(response, 120)
    return service.get_stockout_risk(
        _make_filter(site_key=site_key, drug_code=drug_code, risk_level=risk_level, limit=limit)
    )


# ------------------------------------------------------------------
# 5. GET /dispensing/reconciliation — physical vs calculated stock
# ------------------------------------------------------------------


@router.get("/reconciliation", response_model=list[StockReconciliation])
@limiter.limit("30/minute")
def get_reconciliation(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("dispensing:read"))],
    site_key: int | None = None,
    drug_code: str | None = None,
    limit: int = 100,
) -> list[StockReconciliation]:
    """Return reconciliation report: physical inventory counts vs calculated stock levels."""
    _check_dispensing_plan(limits)
    set_cache_headers(response, 300)
    return service.get_reconciliation(
        _make_filter(site_key=site_key, drug_code=drug_code, limit=limit)
    )
