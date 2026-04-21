"""POS transaction header + line item manipulation request/response models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datapulse.pos.constants import PaymentMethod, TransactionStatus
from datapulse.pos.models.cart import PosCartItem
from datapulse.types import JsonDecimal


class PosTransaction(BaseModel):
    """Internal domain model for a POS transaction."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    terminal_id: int
    staff_id: str
    pharmacist_id: str | None = None
    customer_id: str | None = None
    site_code: str
    subtotal: JsonDecimal
    discount_total: JsonDecimal
    tax_total: JsonDecimal
    grand_total: JsonDecimal
    payment_method: PaymentMethod | None = None
    status: TransactionStatus
    receipt_number: str | None = None
    created_at: datetime
    items: list[PosCartItem] = Field(default_factory=list)


class TransactionResponse(BaseModel):
    """Minimal API response for a POS transaction (list views)."""

    model_config = ConfigDict(frozen=True)

    id: int
    terminal_id: int
    staff_id: str
    customer_id: str | None = None
    grand_total: JsonDecimal
    payment_method: PaymentMethod | None = None
    status: TransactionStatus
    receipt_number: str | None = None
    created_at: datetime


class TransactionDetailResponse(BaseModel):
    """Full API response for a POS transaction including line items."""

    model_config = ConfigDict(frozen=True)

    id: int
    terminal_id: int
    staff_id: str
    pharmacist_id: str | None = None
    customer_id: str | None = None
    site_code: str
    subtotal: JsonDecimal
    discount_total: JsonDecimal
    tax_total: JsonDecimal
    grand_total: JsonDecimal
    payment_method: PaymentMethod | None = None
    status: TransactionStatus
    receipt_number: str | None = None
    created_at: datetime
    items: list[PosCartItem] = Field(default_factory=list)


class AddItemRequest(BaseModel):
    """Request body to add a drug to the active cart."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    quantity: Annotated[Decimal, Field(gt=Decimal("0"))]
    # Optional: override unit price (requires pos:price_override permission)
    override_price: JsonDecimal | None = None
    pharmacist_id: str | None = None


class UpdateItemRequest(BaseModel):
    """Request body to update quantity or price of a cart item."""

    model_config = ConfigDict(frozen=True)

    quantity: Annotated[Decimal, Field(gt=Decimal("0"))]
    override_price: JsonDecimal | None = None
    discount: JsonDecimal | None = None
