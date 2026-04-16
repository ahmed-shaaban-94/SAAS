"""Pydantic request/response models for the POS module.

All models are frozen (immutable) to prevent accidental mutation after
construction. Financial fields use JsonDecimal (Decimal internally,
float in JSON) for precision without JS string-parsing issues.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datapulse.pos.constants import (
    CashDrawerEventType,
    PaymentMethod,
    ReturnReason,
    TerminalStatus,
    TransactionStatus,
)
from datapulse.types import JsonDecimal

# ---------------------------------------------------------------------------
# Cart item (internal + API-facing)
# ---------------------------------------------------------------------------


class PosCartItem(BaseModel):
    """A single line item in a POS cart or completed transaction."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    batch_number: str | None = None
    expiry_date: date | None = None
    quantity: JsonDecimal
    unit_price: JsonDecimal
    discount: JsonDecimal = Decimal("0")
    line_total: JsonDecimal
    is_controlled: bool = False
    pharmacist_id: str | None = None


# ---------------------------------------------------------------------------
# Terminal session
# ---------------------------------------------------------------------------


class TerminalSession(BaseModel):
    """Internal domain model for a POS terminal session."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    site_code: str
    staff_id: str
    terminal_name: str
    status: TerminalStatus
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: JsonDecimal
    closing_cash: JsonDecimal | None = None


class TerminalOpenRequest(BaseModel):
    """Request body to open a new POS terminal session."""

    model_config = ConfigDict(frozen=True)

    site_code: str
    terminal_name: str = "Terminal-1"
    opening_cash: JsonDecimal = Decimal("0")


class TerminalCloseRequest(BaseModel):
    """Request body to close a terminal session and reconcile cash."""

    model_config = ConfigDict(frozen=True)

    closing_cash: JsonDecimal
    notes: str | None = None


class TerminalSessionResponse(BaseModel):
    """API response for a terminal session."""

    model_config = ConfigDict(frozen=True)

    id: int
    site_code: str
    staff_id: str
    terminal_name: str
    status: TerminalStatus
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: JsonDecimal
    closing_cash: JsonDecimal | None = None


# ---------------------------------------------------------------------------
# POS transaction
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Item management requests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Void transaction
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Shift management
# ---------------------------------------------------------------------------


class StartShiftRequest(BaseModel):
    """Request body to start a new cashier shift on a terminal."""

    model_config = ConfigDict(frozen=True)

    terminal_id: int = Field(ge=1)
    opening_cash: JsonDecimal = Decimal("0")


class CloseShiftRequest(BaseModel):
    """Request body to close a cashier shift and record the closing cash total."""

    model_config = ConfigDict(frozen=True)

    closing_cash: JsonDecimal


class ShiftRecord(BaseModel):
    """Internal domain model for a shift record."""

    model_config = ConfigDict(frozen=True)

    id: int
    terminal_id: int
    tenant_id: int
    staff_id: str
    shift_date: date
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: JsonDecimal
    closing_cash: JsonDecimal | None = None
    expected_cash: JsonDecimal | None = None
    variance: JsonDecimal | None = None


class ShiftSummaryResponse(BaseModel):
    """API response summarizing a shift's cash reconciliation."""

    model_config = ConfigDict(frozen=True)

    id: int
    terminal_id: int
    staff_id: str
    shift_date: date
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: JsonDecimal
    closing_cash: JsonDecimal | None = None
    expected_cash: JsonDecimal | None = None
    variance: JsonDecimal | None = None
    transaction_count: int = 0
    total_sales: JsonDecimal = Decimal("0")


class CashCountRequest(BaseModel):
    """Request body to record a mid-shift cash count."""

    model_config = ConfigDict(frozen=True)

    event_type: CashDrawerEventType
    amount: JsonDecimal
    reference_id: str | None = None


class CashDrawerEventResponse(BaseModel):
    """API response for a recorded cash drawer event."""

    model_config = ConfigDict(frozen=True)

    id: int
    terminal_id: int
    event_type: CashDrawerEventType
    amount: JsonDecimal
    reference_id: str | None = None
    timestamp: datetime


# ---------------------------------------------------------------------------
# Product search
# ---------------------------------------------------------------------------


class PosProductResult(BaseModel):
    """Search result for a drug at the POS terminal."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    drug_brand: str | None = None
    drug_cluster: str | None = None
    unit_price: JsonDecimal
    stock_quantity: JsonDecimal
    is_controlled: bool = False
    requires_pharmacist: bool = False


class PosStockInfo(BaseModel):
    """Stock and batch information for a specific drug at a site."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    site_code: str
    quantity_available: JsonDecimal
    batches: list[BatchSummary] = Field(default_factory=list)


class BatchSummary(BaseModel):
    """Summary of a single drug batch at the POS."""

    model_config = ConfigDict(frozen=True)

    batch_number: str
    expiry_date: date | None = None
    quantity_available: JsonDecimal


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


class EmailReceiptRequest(BaseModel):
    """Request body to email a receipt to a customer."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Controlled substance verification
# ---------------------------------------------------------------------------


class PharmacistVerifyRequest(BaseModel):
    """Request body to verify a pharmacist for controlled substance dispensing."""

    model_config = ConfigDict(frozen=True)

    pharmacist_id: str
    # PIN or credential used for verification (not stored, checked in-memory)
    credential: str = Field(min_length=4, max_length=128)
    drug_code: str


class PharmacistVerifyResponse(BaseModel):
    """Response from a successful pharmacist PIN verification.

    The ``token`` is a short-lived HMAC-signed bearer that must be passed
    as ``pharmacist_id`` in subsequent ``add_item`` calls for the same
    ``drug_code``.  Tokens expire after ``TOKEN_TTL_SECONDS`` (5 minutes).
    """

    model_config = ConfigDict(frozen=True)

    token: str
    pharmacist_id: str
    drug_code: str
    expires_at: datetime
