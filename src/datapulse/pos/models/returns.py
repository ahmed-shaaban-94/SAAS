"""Return processing request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from datapulse.pos.constants import ReturnReason
from datapulse.pos.models.cart import PosCartItem
from datapulse.types import JsonDecimal


class ReturnRequest(BaseModel):
    """Request body to process a drug return."""

    model_config = ConfigDict(frozen=True)

    original_transaction_id: int
    items: list[PosCartItem]
    reason: ReturnReason
    refund_method: str = Field(pattern=r"^(cash|credit_note)$")
    notes: str | None = None


class ReturnResponse(BaseModel):
    """Response for a processed return."""

    model_config = ConfigDict(frozen=True)

    id: int
    original_transaction_id: int
    return_transaction_id: int | None = None
    refund_amount: JsonDecimal
    refund_method: str
    reason: ReturnReason
    created_at: datetime


class ReturnDetailResponse(BaseModel):
    """Full return detail including items."""

    model_config = ConfigDict(frozen=True)

    id: int
    original_transaction_id: int
    return_transaction_id: int | None = None
    staff_id: str
    refund_amount: JsonDecimal
    refund_method: str
    reason: ReturnReason
    notes: str | None = None
    created_at: datetime
    items: list[PosCartItem] = Field(default_factory=list)
