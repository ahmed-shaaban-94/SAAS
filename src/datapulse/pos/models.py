"""Pydantic request/response models for the POS module.

All models are frozen (immutable) to prevent accidental mutation after
construction. Financial fields use JsonDecimal (Decimal internally,
float in JSON) for precision without JS string-parsing issues.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

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


# ---------------------------------------------------------------------------
# M1 — Capabilities (§6.6)
# ---------------------------------------------------------------------------


class CapabilitiesDoc(BaseModel):
    """Feature-only capability document returned by GET /pos/capabilities."""

    model_config = ConfigDict(frozen=True)

    server_version: str
    min_client_version: str
    max_client_version: str | None
    idempotency: str
    capabilities: dict[str, bool]
    enforced_policies: dict[str, int]
    tenant_key_endpoint: str
    device_registration_endpoint: str


# ---------------------------------------------------------------------------
# M1 — Tenant signing keys (§8.8)
# ---------------------------------------------------------------------------


class TenantPublicKey(BaseModel):
    """Public Ed25519 verification key advertised to POS clients."""

    model_config = ConfigDict(frozen=True)

    key_id: str
    public_key: str  # base64-url of raw 32-byte public key
    valid_from: datetime
    valid_until: datetime


class TenantKeysResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    keys: list[TenantPublicKey]


# ---------------------------------------------------------------------------
# M1 — Device registration (§8.9)
# ---------------------------------------------------------------------------


class DeviceRegisterRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    terminal_id: int = Field(ge=1)
    public_key: str = Field(min_length=32)  # base64-url raw 32-byte ed25519 pubkey
    device_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class DeviceRegisterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: int
    terminal_id: int
    registered_at: datetime


# ---------------------------------------------------------------------------
# M1 — Offline grants (§8.8)
# ---------------------------------------------------------------------------


class OverrideCodeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    code_id: str
    salt: str
    hash: str
    issued_to_staff_id: str | None = None


class RoleSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    can_checkout: bool = True
    can_void: bool = False
    can_override_price: bool = False
    can_apply_discount: bool = True
    max_discount_pct: int = 15
    can_process_returns: bool = False
    can_open_drawer_no_sale: bool = False
    can_close_shift: bool = True


class OfflineGrantPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    iss: str = "datapulse-pos"
    grant_id: str
    terminal_id: int
    tenant_id: int
    device_fingerprint: str
    staff_id: str
    shift_id: int
    issued_at: datetime
    offline_expires_at: datetime
    role_snapshot: RoleSnapshot
    override_codes: list[OverrideCodeEntry]
    capabilities_version: str = "v1"


class OfflineGrantEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload: OfflineGrantPayload
    signature_ed25519: str  # base64-url Ed25519 signature of payload JSON
    key_id: str  # which tenant key minted the signature


# ---------------------------------------------------------------------------
# M1 — Override token (§8.8.6)
# ---------------------------------------------------------------------------


class OverrideTokenClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    grant_id: str
    code_id: str
    tenant_id: int
    terminal_id: int
    shift_id: int
    action: Literal[
        "retry_override",
        "void",
        "no_sale",
        "price_override",
        "discount_above_limit",
    ]
    action_subject_id: str | None = None
    consumed_at: datetime


class OverrideTokenEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: OverrideTokenClaim
    signature: str  # base64-url Ed25519 signature of claim JSON, signed by the device key


# ---------------------------------------------------------------------------
# M1 — Active terminals (§1.4, §6.6)
# ---------------------------------------------------------------------------


class ActiveTerminalRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    terminal_id: int
    device_fingerprint: str | None
    opened_at: datetime


class ActiveForMeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    active_terminals: list[ActiveTerminalRow]
    multi_terminal_allowed: bool
    max_terminals: int


# ---------------------------------------------------------------------------
# M1 — Atomic commit (§3)
# ---------------------------------------------------------------------------


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


class CommitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: int
    receipt_number: str
    commit_confirmed_at: datetime
    change_due: JsonDecimal = Decimal("0")


# ---------------------------------------------------------------------------
# M1 — Shift close v2 (§3.6)
# ---------------------------------------------------------------------------


class LocalUnresolvedClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    count: int = Field(ge=0)
    digest: str = Field(min_length=10, max_length=200)


class CloseShiftRequestV2(BaseModel):
    """Shift-close with client-reported unresolved-queue claim (§3.6)."""

    model_config = ConfigDict(frozen=True)

    closing_cash: JsonDecimal
    notes: str | None = None
    local_unresolved: LocalUnresolvedClaim


# ---------------------------------------------------------------------------
# M3b — Catalog pull (§pull-sync)
# ---------------------------------------------------------------------------


class CatalogProductEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    drug_brand: str | None = None
    drug_cluster: str | None = None
    drug_category: str | None = None
    is_controlled: bool
    requires_pharmacist: bool
    unit_price: JsonDecimal
    updated_at: str  # ISO timestamp (server wall-clock, not dim_product field)


class CatalogProductPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CatalogProductEntry]
    next_cursor: str | None  # last drug_code in page, or None when exhausted


class CatalogStockEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    drug_code: str
    site_code: str
    batch_number: str
    quantity: JsonDecimal
    expiry_date: date | None = None
    updated_at: str  # loaded_at ISO timestamp used as cursor


class CatalogStockPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CatalogStockEntry]
    next_cursor: str | None  # last loaded_at ISO, or None when exhausted
