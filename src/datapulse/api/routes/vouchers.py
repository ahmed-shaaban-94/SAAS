"""Voucher API endpoints — create / list / validate discount codes.

Mounted at ``/api/v1/pos/vouchers`` and gated by the ``feature_platform``
setting flag (mounted only when POS is enabled). All endpoints require
authentication. Mutating endpoints additionally require the
``pos:voucher:manage`` permission; validation requires
``pos:voucher:validate`` (granted to all POS-facing roles).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_voucher_service
from datapulse.api.limiter import limiter
from datapulse.billing.pos_guard import require_pos_plan
from datapulse.logging import get_logger
from datapulse.pos.models import (
    VoucherCreate,
    VoucherResponse,
    VoucherStatus,
    VoucherValidateRequest,
    VoucherValidateResponse,
)
from datapulse.pos.voucher_service import VoucherService
from datapulse.rbac.dependencies import require_permission

log = get_logger(__name__)

router = APIRouter(
    prefix="/pos/vouchers",
    tags=["pos-vouchers"],
    dependencies=[Depends(get_current_user), Depends(require_pos_plan())],
)

ServiceDep = Annotated[VoucherService, Depends(get_voucher_service)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _tenant_id_of(user: CurrentUser) -> int:
    """Coerce the JWT ``tenant_id`` claim to int; defaults to 1 in dev."""
    return int(user.get("tenant_id") or 1)


@router.post(
    "",
    response_model=VoucherResponse,
    status_code=201,
    dependencies=[Depends(require_permission("pos:voucher:manage"))],
)
@limiter.limit("30/minute")
def create_voucher(
    request: Request,
    payload: VoucherCreate,
    service: ServiceDep,
    user: CurrentUser,
) -> VoucherResponse:
    """Create a new discount voucher for the tenant.

    Returns 409 if (tenant_id, code) already exists.
    """
    return service.create(_tenant_id_of(user), payload)


@router.get(
    "",
    response_model=list[VoucherResponse],
    dependencies=[Depends(require_permission("pos:voucher:manage"))],
)
@limiter.limit("60/minute")
def list_vouchers(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    status: Annotated[VoucherStatus | None, Query()] = None,
) -> list[VoucherResponse]:
    """List all vouchers for the tenant, newest first. Optional status filter."""
    return service.list(_tenant_id_of(user), status=status)


@router.post(
    "/validate",
    response_model=VoucherValidateResponse,
    dependencies=[Depends(require_permission("pos:voucher:validate"))],
)
@limiter.limit("60/minute")
def validate_voucher(
    request: Request,
    payload: VoucherValidateRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> VoucherValidateResponse:
    """Check whether a voucher code can be redeemed by the caller's cart.

    Returns 404 if the code does not exist for the tenant. Returns 400 with
    one of the ``voucher_*`` detail strings if the voucher is inactive,
    expired, not yet active, exhausted, or if ``cart_subtotal`` was supplied
    and fails ``min_purchase``.
    """
    return service.validate(_tenant_id_of(user), payload)
