"""Pydantic models for the Purchase Orders module.

All models are frozen (immutable) to prevent accidental mutation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datapulse.types import JsonDecimal

VALID_PO_STATUSES = frozenset({"draft", "submitted", "partial", "received", "cancelled"})


class POLineItem(BaseModel):
    """A single line item within a purchase order."""

    model_config = ConfigDict(frozen=True)

    line_number: int
    drug_code: str
    drug_name: str | None = None
    ordered_quantity: JsonDecimal
    unit_price: JsonDecimal
    received_quantity: JsonDecimal = Decimal("0")
    line_total: JsonDecimal = Decimal("0")
    fulfillment_pct: JsonDecimal | None = None


class PurchaseOrder(BaseModel):
    """Purchase order summary (header + aggregated line data)."""

    model_config = ConfigDict(frozen=True)

    po_number: str
    po_date: date
    supplier_code: str
    supplier_name: str | None = None
    site_code: str
    status: str
    expected_date: date | None = None
    total_ordered_value: JsonDecimal = Decimal("0")
    total_received_value: JsonDecimal = Decimal("0")
    line_count: int = 0
    notes: str | None = None
    created_by: str | None = None


class PurchaseOrderDetail(BaseModel):
    """Full purchase order with line items."""

    model_config = ConfigDict(frozen=True)

    po_number: str
    po_date: date
    supplier_code: str
    supplier_name: str | None = None
    site_code: str
    status: str
    expected_date: date | None = None
    total_ordered_value: JsonDecimal = Decimal("0")
    total_received_value: JsonDecimal = Decimal("0")
    line_count: int = 0
    notes: str | None = None
    created_by: str | None = None
    lines: list[POLineItem] = Field(default_factory=list)


class POCreateLineRequest(BaseModel):
    """A line item in a PO creation request."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    quantity: JsonDecimal = Field(gt=0)
    unit_price: JsonDecimal = Field(ge=0)


class POCreateRequest(BaseModel):
    """Request body for creating a new purchase order."""

    model_config = ConfigDict(frozen=True)

    po_date: date
    supplier_code: str
    site_code: str
    expected_date: date | None = None
    notes: str | None = None
    lines: list[POCreateLineRequest] = Field(min_length=1)

    @field_validator("supplier_code", "site_code")
    @classmethod
    def _strip_codes(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Code must not be empty")
        return v


class POReceiveLineRequest(BaseModel):
    """A line item in a PO receive request."""

    model_config = ConfigDict(frozen=True)

    line_number: int
    received_quantity: JsonDecimal = Field(ge=0)
    batch_number: str | None = None
    expiry_date: date | None = None


class POReceiveRequest(BaseModel):
    """Request body for recording a PO delivery."""

    model_config = ConfigDict(frozen=True)

    po_number: str
    lines: list[POReceiveLineRequest] = Field(min_length=1)


class POUpdateRequest(BaseModel):
    """Request body for updating a draft purchase order."""

    model_config = ConfigDict(frozen=True)

    expected_date: date | None = None
    notes: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PO_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(sorted(VALID_PO_STATUSES))}"
            )
        return v


class POList(BaseModel):
    """Paginated list of purchase orders."""

    model_config = ConfigDict(frozen=True)

    items: list[PurchaseOrder]
    total: int
    offset: int
    limit: int


class POLineList(BaseModel):
    """List of purchase order lines."""

    model_config = ConfigDict(frozen=True)

    po_number: str
    lines: list[POLineItem]
    total: int


class MarginAnalysisRow(BaseModel):
    """A single row from the margin analysis aggregation."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str | None = None
    drug_brand: str | None = None
    drug_category: str | None = None
    year: int
    month: int
    month_name: str | None = None
    revenue: JsonDecimal
    cogs: JsonDecimal
    gross_margin: JsonDecimal
    margin_pct: JsonDecimal | None = None
    units_sold: JsonDecimal | None = None


class MarginAnalysisList(BaseModel):
    """Margin analysis results."""

    model_config = ConfigDict(frozen=True)

    items: list[MarginAnalysisRow]
    total: int
    year: int | None = None
    month: int | None = None
