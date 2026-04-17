"""Inventory service contract for the POS module.

Defines the interface (Protocol) that POS depends on from the Inventory
module (Plan A). Until Plan A delivers the real ``InventoryService``,
the POS module uses stub dataclasses and ``MockInventoryService``.

When Plan A merges, replace the local stubs with real imports:
    from datapulse.inventory.models import StockLevel, BatchInfo, ReorderAlert, StockMovement
    from datapulse.inventory.service import InventoryService
and remove this file's usage of the stubs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Stub dataclasses — mirror the expected Plan A interface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StockLevel:
    """Current stock levels for a drug at a site."""

    drug_code: str
    site_code: str
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    reorder_point: Decimal


@dataclass(frozen=True)
class BatchInfo:
    """Information about a single drug batch."""

    batch_number: str
    expiry_date: date | None
    quantity_available: Decimal


@dataclass(frozen=True)
class ReorderAlert:
    """Alert for a drug that has fallen below its reorder point."""

    drug_code: str
    site_code: str
    quantity_available: Decimal
    reorder_point: Decimal


@dataclass(frozen=True)
class StockMovement:
    """A recorded stock movement (sale, return, adjustment)."""

    drug_code: str
    site_code: str
    quantity_delta: Decimal  # negative for sales, positive for returns
    batch_number: str | None
    reference_id: str | None  # transaction ID that caused the movement
    movement_type: str  # "sale" | "return" | "adjustment"


# ---------------------------------------------------------------------------
# Protocol — the interface POS depends on
# ---------------------------------------------------------------------------


@runtime_checkable
class InventoryServiceProtocol(Protocol):
    """Async protocol for the Inventory service used by POS.

    All methods are async so they can run inside the FastAPI event loop
    without blocking. The mock implementation (below) satisfies this protocol.
    """

    async def get_stock_level(self, drug_code: str, site_code: str) -> StockLevel:
        """Return current stock levels for a drug at a site."""
        ...

    async def check_batch_expiry(
        self,
        drug_code: str,
        site_code: str,
    ) -> list[BatchInfo]:
        """Return all unexpired batches for a drug sorted by expiry (FEFO)."""
        ...

    async def record_movement(self, movement: StockMovement) -> None:
        """Record a stock movement (fire-and-forget from POS perspective)."""
        ...

    async def get_reorder_alerts(self, site_code: str) -> list[ReorderAlert]:
        """Return all drugs at or below reorder point for a site."""
        ...


# ---------------------------------------------------------------------------
# Mock implementation — used in dev + all POS tests until Plan A merges
# ---------------------------------------------------------------------------


class MockInventoryService:
    """In-memory mock of InventoryService for development and testing.

    Provides sensible defaults; tests override individual methods via
    ``unittest.mock.AsyncMock(spec=MockInventoryService)`` or by directly
    setting attributes on an instance.
    """

    def __init__(self) -> None:
        # Recorded calls for assertion in tests
        self._movements: list[StockMovement] = []

    async def get_stock_level(self, drug_code: str, site_code: str) -> StockLevel:
        """Return a default stock level (100 units available)."""
        return StockLevel(
            drug_code=drug_code,
            site_code=site_code,
            quantity_on_hand=Decimal("100.0000"),
            quantity_reserved=Decimal("0.0000"),
            quantity_available=Decimal("100.0000"),
            reorder_point=Decimal("20.0000"),
        )

    async def check_batch_expiry(
        self,
        drug_code: str,
        site_code: str,
    ) -> list[BatchInfo]:
        """Return a single default batch expiring in June 2027 (FEFO order)."""
        return [
            BatchInfo(
                batch_number="BATCH-2026-001",
                expiry_date=date(2027, 6, 15),
                quantity_available=Decimal("100.0000"),
            )
        ]

    async def record_movement(self, movement: StockMovement) -> None:
        """Record movement in the internal log for test assertions."""
        self._movements.append(movement)

    async def get_reorder_alerts(self, site_code: str) -> list[ReorderAlert]:
        """Return an empty alerts list (no low-stock drugs by default)."""
        return []

    # Test helper --------------------------------------------------------

    def get_recorded_movements(self) -> list[StockMovement]:
        """Return a copy of recorded movements for test assertions."""
        return list(self._movements)

    def reset(self) -> None:
        """Clear recorded state between test cases."""
        self._movements.clear()
