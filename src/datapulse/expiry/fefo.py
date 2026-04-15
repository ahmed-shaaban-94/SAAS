"""FEFO (First Expiry First Out) batch selection algorithm.

Selects batches in ascending expiry order to minimize waste by
consuming the oldest stock first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class BatchSelection:
    """A single batch chosen by the FEFO algorithm."""

    batch_number: str
    expiry_date: date
    available_quantity: Decimal
    allocated_quantity: Decimal


def select_batches_fefo(
    available_batches: list[dict],
    required_quantity: Decimal,
) -> tuple[list[BatchSelection], Decimal]:
    """Select batches using FEFO (First Expiry First Out).

    Iterates batches sorted by expiry_date ASC, allocating as much as
    possible from each batch until the required quantity is fulfilled.

    Args:
        available_batches: List of dicts with at least ``batch_number``,
            ``expiry_date`` (date), and ``current_quantity`` (numeric).
            Batches with zero or negative quantity are skipped.
        required_quantity: Total quantity to fulfil.

    Returns:
        A tuple of:
        - ``selected``: list of :class:`BatchSelection` in FEFO order.
        - ``remaining``: unfulfilled quantity (0 if fully satisfied).
    """
    if required_quantity <= 0:
        return [], Decimal("0")

    selected: list[BatchSelection] = []
    remaining = required_quantity

    for batch in sorted(available_batches, key=lambda b: b["expiry_date"]):
        if remaining <= 0:
            break
        available = Decimal(str(batch["current_quantity"]))
        if available <= 0:
            continue
        allocated = min(available, remaining)
        selected.append(
            BatchSelection(
                batch_number=batch["batch_number"],
                expiry_date=batch["expiry_date"],
                available_quantity=available,
                allocated_quantity=allocated,
            )
        )
        remaining -= allocated

    return selected, max(remaining, Decimal("0"))
