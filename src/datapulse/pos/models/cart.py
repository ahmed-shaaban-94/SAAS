"""Cart-level primitives used across POS transaction and commit flows.

Shared across checkout, transaction, returns, and commit models. Keeps
the cross-module forward references local so Pydantic can resolve them.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


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
    cost_per_unit: JsonDecimal | None = None
