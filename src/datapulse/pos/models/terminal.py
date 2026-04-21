"""Terminal session lifecycle and active-terminal status models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from datapulse.pos.constants import TerminalStatus
from datapulse.types import JsonDecimal


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


class ActiveTerminalRow(BaseModel):
    """One active-terminal entry returned to the client (M1 §1.4, §6.6)."""

    model_config = ConfigDict(frozen=True)

    terminal_id: int
    device_fingerprint: str | None
    opened_at: datetime


class ActiveForMeResponse(BaseModel):
    """Response body for GET /pos/terminals/active-for-me."""

    model_config = ConfigDict(frozen=True)

    active_terminals: list[ActiveTerminalRow]
    multi_terminal_allowed: bool
    max_terminals: int
