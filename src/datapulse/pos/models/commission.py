"""POS shift commission + daily target models (#627 Phase D4)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


class ActiveShiftResponse(BaseModel):
    """The authenticated staff's active shift + commission + target.

    Returned by ``GET /pos/shifts/current``. Extends the standard shift shape
    with:

    * ``commission_earned_egp`` — live-computed sum over the shift's completed
      transactions (``line_total × product_catalog_meta.commission_rate``).
      Zero when no sales yet or no drugs on the commission list.
    * ``daily_sales_target_egp`` — terminal-level target, ``None`` when unset.
    * ``transactions_so_far`` / ``sales_so_far_egp`` — running totals for the
      status-strip progress ring.
    """

    model_config = ConfigDict(frozen=True)

    shift_id: int
    terminal_id: int
    staff_id: str
    shift_date: date
    opened_at: datetime
    opening_cash: JsonDecimal

    commission_earned_egp: JsonDecimal = Decimal("0")
    daily_sales_target_egp: JsonDecimal | None = None
    transactions_so_far: int = 0
    sales_so_far_egp: JsonDecimal = Decimal("0")
