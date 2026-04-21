"""Checkout, void, atomic-commit, and cart-level discount models.

Groups together the REST endpoints that finalize a transaction and the
M1 atomic-commit endpoint used by offline POS clients — both share the
``AppliedDiscount`` primitive and ``voucher_code`` back-compat semantics.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datapulse.pos.constants import PaymentMethod, TransactionStatus
from datapulse.pos.models.cart import PosCartItem
from datapulse.types import JsonDecimal


class AppliedDiscount(BaseModel):
    """Cart-level discount attached to a ``CommitRequest`` or ``CheckoutRequest``.

    One of two sources: a redeemable voucher code or an admin-configured
    promotion. The server routes ``ref`` to the right redemption function
    based on ``source``. Mutually exclusive with the legacy ``voucher_code``
    field (the latter remains for back-compat with offline POS clients that
    have not yet migrated).
    """

    model_config = ConfigDict(frozen=True)

    source: Literal["voucher", "promotion"]
    ref: str  # voucher code, or str(promotion_id) for source='promotion'


class CheckoutRequest(BaseModel):
    """Request body to finalize and pay a POS transaction."""

    model_config = ConfigDict(frozen=True)

    payment_method: PaymentMethod
    # For cash payments: amount tendered by the customer
    cash_tendered: JsonDecimal | None = None
    # For insurance payments: insurance/national ID
    insurance_no: str | None = None
    # Customer ID (optional — walk-in if absent)
    customer_id: str | None = None
    # Override discount applied to the entire transaction
    transaction_discount: JsonDecimal = Decimal("0")
    # Unified cart-level discount (voucher OR promotion). Preferred over
    # ``voucher_code`` — takes precedence when both are present.
    applied_discount: AppliedDiscount | None = None
    # Legacy — still accepted for offline POS clients that send a raw code.
    voucher_code: str | None = None

    @model_validator(mode="after")
    def _one_discount_only(self) -> CheckoutRequest:
        if self.applied_discount is not None and self.voucher_code is not None:
            raise ValueError(
                "applied_discount and voucher_code are mutually exclusive — "
                "send one or the other, not both"
            )
        return self


class CheckoutResponse(BaseModel):
    """Response returned after a successful checkout."""

    model_config = ConfigDict(frozen=True)

    transaction_id: int
    receipt_number: str
    grand_total: JsonDecimal
    payment_method: PaymentMethod
    # Cash change owed to customer (cash payments only)
    change_due: JsonDecimal = Decimal("0")
    status: TransactionStatus
    # Discount amount applied from the redeemed voucher or promotion (0 if none)
    voucher_discount: JsonDecimal = Decimal("0")
    # Populated when a promotion (not a voucher) was applied at checkout
    applied_promotion_id: int | None = None


class VoidRequest(BaseModel):
    """Request body to void a completed transaction (supervisor only)."""

    model_config = ConfigDict(frozen=True)

    reason: str = Field(min_length=3, max_length=500)


class VoidResponse(BaseModel):
    """Audit record returned after a transaction is voided."""

    model_config = ConfigDict(frozen=True)

    id: int
    transaction_id: int
    tenant_id: int
    voided_by: str
    reason: str
    voided_at: datetime


class CommitRequest(BaseModel):
    """Atomic transaction commit payload — draft + items + checkout in one body."""

    model_config = ConfigDict(frozen=True)

    terminal_id: int = Field(ge=1)
    shift_id: int = Field(ge=1)
    staff_id: str
    customer_id: str | None = None
    site_code: str
    items: list[PosCartItem]
    subtotal: JsonDecimal
    discount_total: JsonDecimal = Decimal("0")
    tax_total: JsonDecimal = Decimal("0")
    grand_total: JsonDecimal
    payment_method: PaymentMethod
    cash_tendered: JsonDecimal | None = None
    # Phase 2 — unified cart-level discount (voucher OR promotion). When
    # present, takes precedence over the legacy ``voucher_code`` field.
    applied_discount: AppliedDiscount | None = None
    # Legacy — retained for offline POS clients that still send a raw
    # voucher code. New clients should populate ``applied_discount`` instead.
    voucher_code: str | None = None

    @model_validator(mode="after")
    def _one_discount_only(self) -> CommitRequest:
        if self.applied_discount is not None and self.voucher_code is not None:
            raise ValueError(
                "applied_discount and voucher_code are mutually exclusive — "
                "send one or the other, not both"
            )
        return self


class CommitResponse(BaseModel):
    """Response body for POST /pos/transactions/commit (idempotent)."""

    model_config = ConfigDict(frozen=True)

    transaction_id: int
    receipt_number: str
    commit_confirmed_at: datetime
    change_due: JsonDecimal = Decimal("0")
    # Discount applied via redeemed voucher or promotion (0 if none).
    # Added with a default so cached idempotent replays remain backward-compat.
    voucher_discount: JsonDecimal = Decimal("0")
    # Which promotion (if any) was applied — 0 when a voucher was used.
    applied_promotion_id: int | None = None
