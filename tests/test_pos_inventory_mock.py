"""Tests for the POS inventory contract module.

Validates:
- Stub dataclasses are constructable and frozen
- MockInventoryService returns correct types on all methods
- MockInventoryService satisfies InventoryServiceProtocol at runtime
- Movement recording works for test assertions
- unittest.mock.AsyncMock(spec=MockInventoryService) can replace the mock
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from datapulse.pos.inventory_contract import (
    BatchInfo,
    InventoryServiceProtocol,
    MockInventoryService,
    ReorderAlert,
    StockLevel,
    StockMovement,
)

# ---------------------------------------------------------------------------
# Stub dataclass tests
# ---------------------------------------------------------------------------


class TestStubDataclasses:
    def test_stock_level_construction(self):
        sl = StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("100.0000"),
            quantity_reserved=Decimal("10.0000"),
            quantity_available=Decimal("90.0000"),
            reorder_point=Decimal("20.0000"),
        )
        assert sl.drug_code == "DRUG001"
        assert sl.quantity_available == Decimal("90.0000")

    def test_stock_level_frozen(self):
        sl = StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("100"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("100"),
            reorder_point=Decimal("20"),
        )
        with pytest.raises((TypeError, AttributeError)):
            sl.quantity_available = Decimal("999")  # type: ignore[misc]

    def test_batch_info_construction(self):
        bi = BatchInfo(
            batch_number="BATCH-2026-001",
            expiry_date=date(2027, 6, 15),
            quantity_available=Decimal("50.0000"),
        )
        assert bi.batch_number == "BATCH-2026-001"
        assert bi.expiry_date == date(2027, 6, 15)

    def test_batch_info_no_expiry(self):
        bi = BatchInfo(
            batch_number="BATCH-NO-EXP",
            expiry_date=None,
            quantity_available=Decimal("10.0000"),
        )
        assert bi.expiry_date is None

    def test_reorder_alert_construction(self):
        alert = ReorderAlert(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_available=Decimal("5.0000"),
            reorder_point=Decimal("20.0000"),
        )
        assert alert.quantity_available < alert.reorder_point

    def test_stock_movement_construction(self):
        mv = StockMovement(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_delta=Decimal("-2.0000"),
            batch_number="BATCH-001",
            reference_id="TXN-UUID-123",
            movement_type="sale",
        )
        assert mv.quantity_delta < Decimal("0")
        assert mv.movement_type == "sale"

    def test_stock_movement_frozen(self):
        mv = StockMovement(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_delta=Decimal("-1"),
            batch_number=None,
            reference_id=None,
            movement_type="sale",
        )
        with pytest.raises((TypeError, AttributeError)):
            mv.quantity_delta = Decimal("999")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MockInventoryService — method return types
# ---------------------------------------------------------------------------


class TestMockInventoryService:
    @pytest.fixture
    def mock_svc(self) -> MockInventoryService:
        return MockInventoryService()

    def test_is_protocol_instance(self, mock_svc: MockInventoryService):
        assert isinstance(mock_svc, InventoryServiceProtocol)

    def test_get_stock_level_returns_stock_level(self, mock_svc: MockInventoryService):
        result = asyncio.run(mock_svc.get_stock_level("DRUG001", "SITE01"))
        assert isinstance(result, StockLevel)
        assert result.drug_code == "DRUG001"
        assert result.site_code == "SITE01"
        assert result.quantity_available > Decimal("0")

    def test_check_batch_expiry_returns_list_of_batch_info(self, mock_svc: MockInventoryService):
        result = asyncio.run(mock_svc.check_batch_expiry("DRUG001", "SITE01"))
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(b, BatchInfo) for b in result)

    def test_check_batch_expiry_sorted_fefo(self, mock_svc: MockInventoryService):
        """Default mock returns at least one batch; real FEFO is tested in service."""
        batches = asyncio.run(mock_svc.check_batch_expiry("DRUG001", "SITE01"))
        dates = [b.expiry_date for b in batches if b.expiry_date is not None]
        assert dates == sorted(dates)

    def test_record_movement_returns_none(self, mock_svc: MockInventoryService):
        mv = StockMovement(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_delta=Decimal("-1"),
            batch_number="BATCH-001",
            reference_id="TXN-001",
            movement_type="sale",
        )
        result = asyncio.run(mock_svc.record_movement(mv))
        assert result is None

    def test_record_movement_stores_for_assertions(self, mock_svc: MockInventoryService):
        mv = StockMovement(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_delta=Decimal("-3"),
            batch_number="BATCH-001",
            reference_id="TXN-042",
            movement_type="sale",
        )
        asyncio.run(mock_svc.record_movement(mv))
        recorded = mock_svc.get_recorded_movements()
        assert len(recorded) == 1
        assert recorded[0].reference_id == "TXN-042"

    def test_get_reorder_alerts_returns_empty_list(self, mock_svc: MockInventoryService):
        result = asyncio.run(mock_svc.get_reorder_alerts("SITE01"))
        assert isinstance(result, list)
        assert result == []

    def test_reset_clears_movements(self, mock_svc: MockInventoryService):
        mv = StockMovement(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_delta=Decimal("-1"),
            batch_number=None,
            reference_id=None,
            movement_type="sale",
        )
        asyncio.run(mock_svc.record_movement(mv))
        assert len(mock_svc.get_recorded_movements()) == 1

        mock_svc.reset()
        assert len(mock_svc.get_recorded_movements()) == 0

    def test_multiple_movements_recorded(self, mock_svc: MockInventoryService):
        for i in range(3):
            mv = StockMovement(
                drug_code=f"DRUG00{i}",
                site_code="SITE01",
                quantity_delta=Decimal("-1"),
                batch_number=None,
                reference_id=f"TXN-{i}",
                movement_type="sale",
            )
            asyncio.run(mock_svc.record_movement(mv))

        assert len(mock_svc.get_recorded_movements()) == 3

    def test_get_recorded_movements_returns_copy(self, mock_svc: MockInventoryService):
        """Mutating the returned list must not affect internal state."""
        movements = mock_svc.get_recorded_movements()
        movements.append(None)  # type: ignore[arg-type]
        assert len(mock_svc.get_recorded_movements()) == 0


# ---------------------------------------------------------------------------
# AsyncMock compatibility — confirm spec works for test doubles
# ---------------------------------------------------------------------------


class TestAsyncMockCompatibility:
    """Verify that AsyncMock(spec=MockInventoryService) works as expected.

    In POS service tests, the inventory dependency is replaced with:
        inventory_mock = AsyncMock(spec=MockInventoryService)
    This test suite confirms the spec doesn't break the mock.
    """

    def test_async_mock_has_all_methods(self):
        mock = AsyncMock(spec=MockInventoryService)
        assert hasattr(mock, "get_stock_level")
        assert hasattr(mock, "check_batch_expiry")
        assert hasattr(mock, "record_movement")
        assert hasattr(mock, "get_reorder_alerts")

    def test_async_mock_get_stock_level_configurable(self):
        mock = AsyncMock(spec=MockInventoryService)
        mock.get_stock_level.return_value = StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("50"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("50"),
            reorder_point=Decimal("10"),
        )
        result = asyncio.run(mock.get_stock_level("DRUG001", "SITE01"))
        assert isinstance(result, StockLevel)
        assert result.quantity_available == Decimal("50")

    def test_async_mock_out_of_stock_scenario(self):
        mock = AsyncMock(spec=MockInventoryService)
        mock.get_stock_level.return_value = StockLevel(
            drug_code="DRUG999",
            site_code="SITE01",
            quantity_on_hand=Decimal("0"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("0"),
            reorder_point=Decimal("5"),
        )
        result = asyncio.run(mock.get_stock_level("DRUG999", "SITE01"))
        assert result.quantity_available == Decimal("0")
