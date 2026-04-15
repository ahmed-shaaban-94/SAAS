"""Purchase Orders API endpoints.

Provides 7 PO endpoints + 1 margin analysis endpoint.
All endpoints are gated by the purchase_orders plan feature flag.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_po_service, get_tenant_plan_limits
from datapulse.billing.plans import PlanLimits
from datapulse.purchase_orders.models import (
    MarginAnalysisList,
    POCreateRequest,
    POLineList,
    POList,
    POReceiveRequest,
    POUpdateRequest,
    PurchaseOrder,
    PurchaseOrderDetail,
)
from datapulse.purchase_orders.service import PurchaseOrderService
from datapulse.rbac.dependencies import require_permission

router = APIRouter(
    prefix="/purchase-orders",
    tags=["purchase-orders"],
    dependencies=[Depends(get_current_user)],
)

margins_router = APIRouter(
    prefix="/margins",
    tags=["margins"],
    dependencies=[Depends(get_current_user)],
)

POServiceDep = Annotated[PurchaseOrderService, Depends(get_po_service)]
LimitsDep = Annotated[PlanLimits, Depends(get_tenant_plan_limits)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _check_po_feature(limits: PlanLimits) -> None:
    if not limits.purchase_orders:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "feature_not_available",
                "feature": "purchase_orders",
                "message": "Purchase Orders is not available on your current plan. "
                "Upgrade to Pro or Enterprise to enable this feature.",
            },
        )


# ── GET /purchase-orders ──────────────────────────────────────────────────────


@router.get(
    "",
    response_model=POList,
    dependencies=[Depends(require_permission("purchase_orders:read"))],
)
def list_purchase_orders(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    supplier_code: Annotated[str | None, Query(description="Filter by supplier")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> POList:
    """List purchase orders with optional status/supplier filter."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.list_pos(
        tenant_id=tenant_id,
        status=status,
        supplier_code=supplier_code,
        offset=offset,
        limit=limit,
    )


# ── POST /purchase-orders ─────────────────────────────────────────────────────


@router.post(
    "",
    response_model=PurchaseOrder,
    status_code=201,
    dependencies=[Depends(require_permission("purchase_orders:write"))],
)
def create_purchase_order(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    body: POCreateRequest,
) -> PurchaseOrder:
    """Create a new purchase order (status = draft)."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    created_by = user.get("sub")
    return service.create_po(body, tenant_id, created_by=created_by)


# ── GET /purchase-orders/{po_number} ─────────────────────────────────────────


@router.get(
    "/{po_number}",
    response_model=PurchaseOrderDetail,
    dependencies=[Depends(require_permission("purchase_orders:read"))],
)
def get_purchase_order(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    po_number: str,
) -> PurchaseOrderDetail:
    """Get full PO detail including all line items."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.get_po_detail(po_number, tenant_id)


# ── PUT /purchase-orders/{po_number} ─────────────────────────────────────────


@router.put(
    "/{po_number}",
    response_model=PurchaseOrder,
    dependencies=[Depends(require_permission("purchase_orders:write"))],
)
def update_purchase_order(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    po_number: str,
    body: POUpdateRequest,
) -> PurchaseOrder:
    """Update a purchase order (draft/submitted only)."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.update_po(po_number, tenant_id, body)


# ── POST /purchase-orders/{po_number}/receive ─────────────────────────────────


@router.post(
    "/{po_number}/receive",
    response_model=PurchaseOrder,
    dependencies=[Depends(require_permission("purchase_orders:write"))],
)
def receive_purchase_order(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    po_number: str,
    body: POReceiveRequest,
    receipt_date: Annotated[
        date | None,
        Query(description="Date of receipt (defaults to today)"),
    ] = None,
) -> PurchaseOrder:
    """Record delivery of goods against a purchase order.

    This endpoint:
    1. Updates received_quantity on each delivered line
    2. Creates bronze.stock_receipts entries that feed into fct_stock_movements
    3. Recalculates PO status (partial if incomplete, received if fully filled)
    """
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))

    # Ensure path param matches body
    if body.po_number != po_number:
        raise HTTPException(
            status_code=422,
            detail="po_number in path must match po_number in request body",
        )

    return service.receive_po(body, tenant_id, receipt_date=receipt_date)


# ── POST /purchase-orders/{po_number}/cancel ─────────────────────────────────


@router.post(
    "/{po_number}/cancel",
    response_model=PurchaseOrder,
    dependencies=[Depends(require_permission("purchase_orders:write"))],
)
def cancel_purchase_order(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    po_number: str,
) -> PurchaseOrder:
    """Cancel a purchase order (draft/submitted only)."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.cancel_po(po_number, tenant_id)


# ── GET /purchase-orders/{po_number}/lines ────────────────────────────────────


@router.get(
    "/{po_number}/lines",
    response_model=POLineList,
    dependencies=[Depends(require_permission("purchase_orders:read"))],
)
def get_po_lines(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    po_number: str,
) -> POLineList:
    """Get all line items for a purchase order."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.get_lines(po_number, tenant_id)


# ── GET /margins/analysis ─────────────────────────────────────────────────────


@margins_router.get(
    "/analysis",
    response_model=MarginAnalysisList,
    dependencies=[Depends(require_permission("purchase_orders:read"))],
)
def get_margin_analysis(
    service: POServiceDep,
    limits: LimitsDep,
    user: CurrentUser,
    year: Annotated[int | None, Query(description="Filter by year")] = None,
    month: Annotated[int | None, Query(ge=1, le=12, description="Filter by month")] = None,
    drug_code: Annotated[str | None, Query(description="Filter by drug code")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> MarginAnalysisList:
    """Get margin analysis: revenue vs COGS per product per month."""
    _check_po_feature(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    return service.get_margin_analysis(
        tenant_id=tenant_id,
        year=year,
        month=month,
        drug_code=drug_code,
        offset=offset,
        limit=limit,
    )
