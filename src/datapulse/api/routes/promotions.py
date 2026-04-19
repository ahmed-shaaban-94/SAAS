"""Promotion API endpoints — admin CRUD + cashier eligibility.

Mounted at ``/api/v1/pos/promotions`` and gated by ``feature_platform``.
Mutating endpoints require ``pos:promotion:manage``. The eligibility
endpoint requires ``pos:promotion:apply`` (granted to all POS-facing
roles). Promotions are NEVER auto-applied — the cashier picks from the
list returned by ``POST /eligible`` and includes the chosen promotion
in ``CommitRequest.applied_discount``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_promotion_service
from datapulse.api.limiter import limiter
from datapulse.billing.pos_guard import require_pos_plan
from datapulse.logging import get_logger
from datapulse.pos.models import (
    EligiblePromotionsRequest,
    EligiblePromotionsResponse,
    PromotionCreate,
    PromotionResponse,
    PromotionStatus,
    PromotionStatusUpdate,
    PromotionUpdate,
)
from datapulse.pos.promotion_service import PromotionService
from datapulse.rbac.dependencies import require_permission

log = get_logger(__name__)

router = APIRouter(
    prefix="/pos/promotions",
    tags=["pos-promotions"],
    dependencies=[Depends(get_current_user), Depends(require_pos_plan())],
)

ServiceDep = Annotated[PromotionService, Depends(get_promotion_service)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _tenant_id_of(user: CurrentUser) -> int:
    """Coerce the JWT ``tenant_id`` claim to int; defaults to 1 in dev."""
    return int(user.get("tenant_id") or 1)


# ---------------------------------------------------------------------------
# Admin — CRUD
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PromotionResponse,
    status_code=201,
    dependencies=[Depends(require_permission("pos:promotion:manage"))],
)
@limiter.limit("30/minute")
def create_promotion(
    request: Request,
    payload: PromotionCreate,
    service: ServiceDep,
    user: CurrentUser,
) -> PromotionResponse:
    """Create a new promotion. Starts paused — admin activates explicitly."""
    return service.create(_tenant_id_of(user), payload)


@router.get(
    "",
    response_model=list[PromotionResponse],
    dependencies=[Depends(require_permission("pos:promotion:manage"))],
)
@limiter.limit("60/minute")
def list_promotions(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    status: Annotated[PromotionStatus | None, Query()] = None,
) -> list[PromotionResponse]:
    """List tenant promotions, newest first. Optional status filter."""
    return service.list_all(_tenant_id_of(user), status=status)


@router.get(
    "/{promotion_id}",
    response_model=PromotionResponse,
    dependencies=[Depends(require_permission("pos:promotion:manage"))],
)
@limiter.limit("60/minute")
def get_promotion(
    request: Request,
    promotion_id: int,
    service: ServiceDep,
    user: CurrentUser,
) -> PromotionResponse:
    """Fetch one promotion including scope items/categories + usage audit."""
    promo = service.get(_tenant_id_of(user), promotion_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="promotion_not_found")
    return promo


@router.patch(
    "/{promotion_id}",
    response_model=PromotionResponse,
    dependencies=[Depends(require_permission("pos:promotion:manage"))],
)
@limiter.limit("30/minute")
def update_promotion(
    request: Request,
    promotion_id: int,
    payload: PromotionUpdate,
    service: ServiceDep,
    user: CurrentUser,
) -> PromotionResponse:
    """Partial update — all fields optional. Scope joins rewritten when scope changes."""
    return service.update(_tenant_id_of(user), promotion_id, payload)


@router.patch(
    "/{promotion_id}/status",
    response_model=PromotionResponse,
    dependencies=[Depends(require_permission("pos:promotion:manage"))],
)
@limiter.limit("30/minute")
def set_promotion_status(
    request: Request,
    promotion_id: int,
    payload: PromotionStatusUpdate,
    service: ServiceDep,
    user: CurrentUser,
) -> PromotionResponse:
    """Toggle between ``active`` and ``paused``. ``expired`` is auto-managed."""
    return service.set_status(_tenant_id_of(user), promotion_id, PromotionStatus(payload.status))


# ---------------------------------------------------------------------------
# Cashier — eligibility
# ---------------------------------------------------------------------------


@router.post(
    "/eligible",
    response_model=EligiblePromotionsResponse,
    dependencies=[Depends(require_permission("pos:promotion:apply"))],
)
@limiter.limit("120/minute")
def list_eligible_promotions(
    request: Request,
    payload: EligiblePromotionsRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> EligiblePromotionsResponse:
    """Return promotions the cashier can apply to the current cart.

    Evaluates active + in-window promotions against the cart's drug codes,
    clusters, and subtotal. Returns the list with a preview discount each
    promotion would yield so the UI can show \"Save EGP X\".
    """
    return service.list_eligible(_tenant_id_of(user), payload)
