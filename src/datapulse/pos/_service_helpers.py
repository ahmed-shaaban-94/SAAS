"""Module-level helpers shared by the :class:`PosService` mixins.

Pure functions — no instance state. Kept separate from ``service.py`` so the
domain mixins can import them without re-importing the facade class.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from datapulse.pos.constants import CONTROLLED_CATEGORIES
from datapulse.pos.inventory_contract import BatchInfo


def to_decimal(value: Any) -> Decimal:
    """Coerce an int/float/str/Decimal/None into a Decimal (None -> 0)."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def is_controlled(category: str | None) -> bool:
    """Return True when the drug category is in the controlled-substance list."""
    if not category:
        return False
    return category.lower() in CONTROLLED_CATEGORIES


def build_receipt_number(tenant_id: int, transaction_id: int) -> str:
    """Deterministic receipt number: ``R{YYYYMMDD}-{tenant}-{txn_id}``."""
    today = datetime.now(tz=UTC).strftime("%Y%m%d")
    return f"R{today}-{tenant_id}-{transaction_id}"


def select_fefo_batch(
    batches: list[BatchInfo],
    requested_qty: Decimal,
) -> BatchInfo | None:
    """Pick the earliest-expiring batch whose ``quantity_available`` >= requested.

    Implements **First-Expired-First-Out** (FEFO). Batches without an expiry
    date are considered last (treated as far-future). Returns ``None`` when no
    single batch can satisfy the request — the caller should then either
    decline the line or split across batches.
    """
    far_future = date.max
    sorted_batches = sorted(
        batches,
        key=lambda b: (b.expiry_date or far_future, b.batch_number),
    )
    for batch in sorted_batches:
        if batch.quantity_available >= requested_qty:
            return batch
    return None
