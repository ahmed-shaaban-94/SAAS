"""Shift lifecycle, cash drawer, and shift-close v2 models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.pos.constants import CashDrawerEventType
from datapulse.types import JsonDecimal


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


class LocalUnresolvedClaim(BaseModel):
    """Client-reported digest of any unresolved local queue rows at shift close."""

    model_config = ConfigDict(frozen=True)

    count: int = Field(ge=0)
    digest: str = Field(min_length=10, max_length=200)


class CloseShiftRequestV2(BaseModel):
    """Shift-close with client-reported unresolved-queue claim (§3.6)."""

    model_config = ConfigDict(frozen=True)

    closing_cash: JsonDecimal
    notes: str | None = None
    local_unresolved: LocalUnresolvedClaim
