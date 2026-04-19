"""Voucher service — business logic for the POS discount-code engine.

Most methods are thin pass-throughs to :class:`VoucherRepository`.
``validate()`` exposes the read-only validation used by the
``POST /api/v1/pos/vouchers/validate`` endpoint (without incrementing uses).
``compute_discount()`` is a pure static helper that derives the discount
amount to subtract from a subtotal — used at redemption time by
:func:`datapulse.pos.commit.atomic_commit`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException

from datapulse.logging import get_logger
from datapulse.pos.models import (
    VoucherCreate,
    VoucherResponse,
    VoucherStatus,
    VoucherType,
    VoucherValidateRequest,
    VoucherValidateResponse,
)
from datapulse.pos.voucher_repository import VoucherRepository

log = get_logger(__name__)

# Money precision used throughout the POS module (NUMERIC(18,4)).
_MONEY_QUANT = Decimal("0.0001")


class VoucherService:
    """Business logic for voucher creation, listing, validation, and redemption helpers."""

    def __init__(self, repo: VoucherRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, tenant_id: int, payload: VoucherCreate) -> VoucherResponse:
        """Create a new voucher for the tenant."""
        return self._repo.create(tenant_id, payload)

    def list(
        self,
        tenant_id: int,
        *,
        status: VoucherStatus | None = None,
    ) -> list[VoucherResponse]:
        """List vouchers for the tenant, optionally filtered by status."""
        return self._repo.list_for_tenant(tenant_id, status=status)

    # ------------------------------------------------------------------
    # Validation (read-only)
    # ------------------------------------------------------------------

    def validate(
        self,
        tenant_id: int,
        req: VoucherValidateRequest,
    ) -> VoucherValidateResponse:
        """Validate a voucher code without redeeming it.

        Raises 404 when the code is unknown. Raises 400 with a precise detail
        when the voucher is inactive, expired, not yet active, exhausted, or
        when ``cart_subtotal`` is supplied and fails the ``min_purchase`` gate.
        """
        voucher = self._repo.get_by_code(tenant_id, req.code)
        if voucher is None:
            raise HTTPException(status_code=404, detail="voucher_not_found")
        now = datetime.now(UTC)
        self._assert_redeemable(voucher, now=now, cart_subtotal=req.cart_subtotal)
        remaining = voucher.max_uses - voucher.uses
        return VoucherValidateResponse(
            code=voucher.code,
            discount_type=voucher.discount_type,
            value=voucher.value,
            remaining_uses=remaining,
            expires_at=voucher.ends_at,
            min_purchase=voucher.min_purchase,
        )

    @staticmethod
    def _assert_redeemable(
        voucher: VoucherResponse,
        *,
        now: datetime,
        cart_subtotal: Decimal | None,
    ) -> None:
        """Raise HTTPException(400) if the voucher is not currently redeemable."""
        if voucher.status != VoucherStatus.active:
            raise HTTPException(status_code=400, detail="voucher_inactive")
        if voucher.starts_at is not None and now < voucher.starts_at:
            raise HTTPException(status_code=400, detail="voucher_not_yet_active")
        if voucher.ends_at is not None and now > voucher.ends_at:
            raise HTTPException(status_code=400, detail="voucher_expired")
        if voucher.uses >= voucher.max_uses:
            raise HTTPException(status_code=400, detail="voucher_max_uses_reached")
        if (
            voucher.min_purchase is not None
            and cart_subtotal is not None
            and cart_subtotal < voucher.min_purchase
        ):
            raise HTTPException(status_code=400, detail="voucher_min_purchase_unmet")

    # ------------------------------------------------------------------
    # Discount computation — pure helper
    # ------------------------------------------------------------------

    @staticmethod
    def compute_discount(
        discount_type: VoucherType,
        value: Decimal,
        subtotal: Decimal,
    ) -> Decimal:
        """Return the absolute discount amount to subtract from ``subtotal``.

        Never exceeds ``subtotal`` (an amount voucher caps at subtotal).
        Percent vouchers compute ``subtotal * value / 100`` and quantize to
        4 decimal places with HALF_UP rounding to stay consistent with the
        rest of the POS financial math (:data:`_MONEY_QUANT`).
        """
        if subtotal <= 0:
            return Decimal("0")
        if discount_type == VoucherType.amount:
            return min(value, subtotal).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
        # percent
        raw = (subtotal * value) / Decimal("100")
        quantized = raw.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
        return min(quantized, subtotal)
