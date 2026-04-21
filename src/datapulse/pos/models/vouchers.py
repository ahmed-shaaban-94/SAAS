"""Voucher discount engine (Phase 1) — code → discount lookups and validation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from datapulse.types import JsonDecimal


class VoucherType(StrEnum):
    """Kind of discount produced by a voucher when redeemed."""

    amount = "amount"
    percent = "percent"


class VoucherStatus(StrEnum):
    """Lifecycle states of a voucher."""

    active = "active"
    redeemed = "redeemed"
    expired = "expired"
    void = "void"


# Voucher codes are uppercase alphanumeric with hyphens / underscores — 3..64.
VoucherCodeStr = Annotated[
    str,
    StringConstraints(min_length=3, max_length=64, pattern=r"^[A-Z0-9_-]+$"),
]


class VoucherCreate(BaseModel):
    """Request body to create a new voucher."""

    model_config = ConfigDict(frozen=True)

    code: VoucherCodeStr
    discount_type: VoucherType
    value: JsonDecimal  # > 0; for percent must be 0 < value <= 100
    max_uses: Annotated[int, Field(ge=1)] = 1
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    min_purchase: JsonDecimal | None = None

    @model_validator(mode="after")
    def _validate_value_bounds(self) -> VoucherCreate:
        if self.value <= 0:
            raise ValueError("value must be > 0")
        if self.discount_type == VoucherType.percent and self.value > Decimal("100"):
            raise ValueError("percent voucher value must be <= 100")
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("ends_at must be after starts_at")
        return self


class VoucherResponse(BaseModel):
    """API response representing a single voucher."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    code: str
    discount_type: VoucherType
    value: JsonDecimal
    max_uses: int
    uses: int
    status: VoucherStatus
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    min_purchase: JsonDecimal | None = None
    redeemed_txn_id: int | None = None
    created_at: datetime


class VoucherValidateRequest(BaseModel):
    """Request body for POST /pos/vouchers/validate."""

    model_config = ConfigDict(frozen=True)

    code: str
    # Optional cart subtotal — if provided, server also verifies min_purchase.
    cart_subtotal: JsonDecimal | None = None


class VoucherValidateResponse(BaseModel):
    """Returned by POST /pos/vouchers/validate when the code is redeemable."""

    model_config = ConfigDict(frozen=True)

    code: str
    discount_type: VoucherType
    value: JsonDecimal
    remaining_uses: int
    expires_at: datetime | None = None
    min_purchase: JsonDecimal | None = None
