"""Tests for the InventoryAdapter — bridges real services to POS protocol.

Validates that the adapter correctly translates between the real
InventoryService/ExpiryService (sync, filter-based) and the POS
InventoryServiceProtocol (async, simple params).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from datapulse.expiry.models import BatchInfo as ExpiryBatchInfo
from datapulse.expiry.service import ExpiryService
from datapulse.inventory.models import ReorderAlert as InvReorderAlert
from datapulse.inventory.models import StockLevel as InvStockLevel
from datapulse.inventory.service import InventoryService
from datapulse.pos.inventory_adapter import InventoryAdapter
from datapulse.pos.inventory_contract import (
    InventoryServiceProtocol,
    StockMovement,
)


@pytest.fixture()
def mock_inv_service():
    return create_autospec(InventoryService, instance=True)


@pytest.fixture()
def mock_exp_service():
    return create_autospec(ExpiryService, instance=True)


@pytest.fixture()
def adapter(mock_inv_service, mock_exp_service):
    return InventoryAdapter(mock_inv_service, mock_exp_service)


class TestAdapterSatisfiesProtocol:
    """The adapter must satisfy the InventoryServiceProtocol at runtime."""

    def test_adapter_is_protocol_instance(self, adapter):
        """InventoryAdapter satisfies InventoryServiceProtocol (runtime_checkable)."""
        assert isinstance(adapter, InventoryServiceProtocol)


class TestGetStockLevel:
    """get_stock_level maps real stock to POS StockLevel."""

    @pytest.mark.asyncio()
    async def test_returns_stock_level_from_real_service(self, adapter, mock_inv_service):
        mock_inv_service.get_stock_level_detail.return_value = [
            InvStockLevel(
                product_key=1,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                drug_brand="GenPharma",
                site_key=1,
                site_code="SITE01",
                site_name="Main",
                current_quantity=Decimal("150"),
                total_received=Decimal("500"),
                total_dispensed=Decimal("350"),
                total_wastage=Decimal("0"),
            )
        ]
        mock_inv_service.get_reorder_alerts.return_value = []

        result = await adapter.get_stock_level("PARA500", "SITE01")

        assert result.drug_code == "PARA500"
        assert result.quantity_available == Decimal("150")

    @pytest.mark.asyncio()
    async def test_returns_zero_when_no_stock(self, adapter, mock_inv_service):
        mock_inv_service.get_stock_level_detail.return_value = []
        mock_inv_service.get_reorder_alerts.return_value = []

        result = await adapter.get_stock_level("UNKNOWN", "SITE01")

        assert result.quantity_available == Decimal("0")

    @pytest.mark.asyncio()
    async def test_includes_reorder_point_from_alerts(self, adapter, mock_inv_service):
        mock_inv_service.get_stock_level_detail.return_value = [
            InvStockLevel(
                product_key=1,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                drug_brand="GenPharma",
                site_key=1,
                site_code="SITE01",
                site_name="Main",
                current_quantity=Decimal("30"),
                total_received=Decimal("100"),
                total_dispensed=Decimal("70"),
                total_wastage=Decimal("0"),
            )
        ]
        mock_inv_service.get_reorder_alerts.return_value = [
            InvReorderAlert(
                product_key=1,
                site_key=1,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                site_code="SITE01",
                current_quantity=Decimal("30"),
                reorder_point=Decimal("50"),
                reorder_quantity=Decimal("200"),
            )
        ]

        result = await adapter.get_stock_level("PARA500", "SITE01")

        assert result.reorder_point == Decimal("50")


class TestCheckBatchExpiry:
    """check_batch_expiry maps real batches to POS BatchInfo list."""

    @pytest.mark.asyncio()
    async def test_returns_active_batches_sorted_fefo(self, adapter, mock_exp_service):
        mock_exp_service.get_batches.return_value = [
            ExpiryBatchInfo(
                batch_key=2,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                site_code="SITE01",
                batch_number="B002",
                expiry_date=date(2027, 12, 31),
                current_quantity=Decimal("50"),
                days_to_expiry=625,
                alert_level="safe",
                computed_status="active",
            ),
            ExpiryBatchInfo(
                batch_key=1,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                site_code="SITE01",
                batch_number="B001",
                expiry_date=date(2027, 6, 15),
                current_quantity=Decimal("100"),
                days_to_expiry=425,
                alert_level="safe",
                computed_status="active",
            ),
        ]

        result = await adapter.check_batch_expiry("PARA500", "SITE01")

        assert len(result) == 2
        assert result[0].batch_number == "B001"
        assert result[1].batch_number == "B002"

    @pytest.mark.asyncio()
    async def test_excludes_quarantined_and_written_off(self, adapter, mock_exp_service):
        mock_exp_service.get_batches.return_value = [
            ExpiryBatchInfo(
                batch_key=1,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                site_code="SITE01",
                batch_number="B001",
                expiry_date=date(2027, 6, 15),
                current_quantity=Decimal("100"),
                days_to_expiry=425,
                alert_level="safe",
                computed_status="active",
            ),
            ExpiryBatchInfo(
                batch_key=2,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                site_code="SITE01",
                batch_number="B002",
                expiry_date=date(2026, 1, 1),
                current_quantity=Decimal("50"),
                days_to_expiry=-105,
                alert_level="expired",
                computed_status="quarantined",
            ),
        ]

        result = await adapter.check_batch_expiry("PARA500", "SITE01")

        assert len(result) == 1
        assert result[0].batch_number == "B001"


class TestRecordMovement:
    """record_movement translates POS movements to inventory adjustments."""

    @pytest.mark.asyncio()
    async def test_sale_movement_creates_adjustment(self, adapter, mock_inv_service):
        movement = StockMovement(
            drug_code="PARA500",
            site_code="SITE01",
            quantity_delta=Decimal("-5"),
            batch_number="B001",
            reference_id="POS-R20260416-1-101",
            movement_type="sale",
        )

        await adapter.record_movement(movement)

        mock_inv_service.create_adjustment.assert_called_once()
        call_args = mock_inv_service.create_adjustment.call_args
        request = call_args[1]["request"] if "request" in call_args[1] else call_args[0][1]
        assert request.drug_code == "PARA500"
        assert request.quantity == Decimal("-5")
        assert "sale" in request.reason.lower()


class TestGetReorderAlerts:
    """get_reorder_alerts filters by site_code."""

    @pytest.mark.asyncio()
    async def test_filters_alerts_by_site(self, adapter, mock_inv_service):
        mock_inv_service.get_reorder_alerts.return_value = [
            InvReorderAlert(
                product_key=1,
                site_key=1,
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                site_code="SITE01",
                current_quantity=Decimal("15"),
                reorder_point=Decimal("50"),
                reorder_quantity=Decimal("200"),
            ),
            InvReorderAlert(
                product_key=2,
                site_key=2,
                drug_code="AMOX250",
                drug_name="Amoxicillin 250mg",
                site_code="SITE02",
                current_quantity=Decimal("10"),
                reorder_point=Decimal("30"),
                reorder_quantity=Decimal("100"),
            ),
        ]

        result = await adapter.get_reorder_alerts("SITE01")

        assert len(result) == 1
        assert result[0].drug_code == "PARA500"
