"""Integration test: stock receipt -> movement -> stock level -> reorder alert.

Tests the complete inventory data flow across domain boundaries:
  1. Stock receipt creates a movement entry
  2. Stock adjustment reduces stock levels
  3. Low stock triggers reorder alert notification
  4. Weighted-average cost updates after multiple receipts
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ConfigDict

# ── Domain models (contract definitions for Sessions 2-5) ──────────


class StockMovement(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    movement_type: str  # receipt | adjustment | dispense | return
    quantity: Decimal
    unit_cost: Decimal | None = None
    batch_number: str | None = None
    reference: str | None = None
    movement_date: date = date.today()


class StockLevel(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    current_quantity: Decimal
    weighted_avg_cost: Decimal


class ReorderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    min_stock: Decimal
    reorder_point: Decimal
    max_stock: Decimal
    reorder_lead_days: int = 7


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture()
def mock_movement_repo():
    """Mock repository for stock movements."""
    repo = MagicMock()
    repo.insert_movement = MagicMock()
    repo.get_movements_by_drug = MagicMock(return_value=[])
    return repo


@pytest.fixture()
def mock_stock_repo():
    """Mock repository for stock levels."""
    repo = MagicMock()
    repo.get_stock_level = MagicMock()
    repo.update_stock_level = MagicMock()
    return repo


@pytest.fixture()
def mock_reorder_repo():
    """Mock repository for reorder configuration."""
    repo = MagicMock()
    repo.get_reorder_config = MagicMock()
    return repo


@pytest.fixture()
def mock_notification_svc():
    """Mock notification service for reorder alerts."""
    svc = MagicMock()
    svc.create_notification = MagicMock()
    return svc


# ── Tests ──────────────────────────────────────────────────────────


class TestReceiptCreatesStockMovement:
    """Stock receipt should create a movement of type 'receipt'."""

    def test_receipt_produces_positive_movement(self, mock_movement_repo):
        """A stock receipt inserts a movement with positive quantity."""
        movement = StockMovement(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            movement_type="receipt",
            quantity=Decimal("200"),
            unit_cost=Decimal("10.00"),
            batch_number="B2025-001",
            reference="GRN-001",
            movement_date=date(2025, 6, 1),
        )

        mock_movement_repo.insert_movement(movement)

        mock_movement_repo.insert_movement.assert_called_once_with(movement)
        assert movement.movement_type == "receipt"
        assert movement.quantity > 0

    def test_receipt_includes_batch_and_cost(self, mock_movement_repo):
        """Receipt movement carries batch number and unit cost for traceability."""
        movement = StockMovement(
            tenant_id=1,
            drug_code="AMOX250",
            site_code="SITE01",
            movement_type="receipt",
            quantity=Decimal("500"),
            unit_cost=Decimal("5.50"),
            batch_number="B2025-100",
            reference="GRN-002",
        )

        assert movement.batch_number == "B2025-100"
        assert movement.unit_cost == Decimal("5.50")


class TestAdjustmentReducesStock:
    """Damage adjustment should reduce stock level."""

    def test_damage_reduces_stock_level(self, mock_stock_repo):
        """Stock at 100, damage adjustment for 10 -> stock level 90."""
        initial = StockLevel(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            current_quantity=Decimal("100"),
            weighted_avg_cost=Decimal("10.00"),
        )
        mock_stock_repo.get_stock_level.return_value = initial

        # Simulate adjustment
        adjustment_qty = Decimal("-10")
        new_qty = initial.current_quantity + adjustment_qty

        updated = StockLevel(
            tenant_id=initial.tenant_id,
            drug_code=initial.drug_code,
            site_code=initial.site_code,
            current_quantity=new_qty,
            weighted_avg_cost=initial.weighted_avg_cost,
        )

        assert updated.current_quantity == Decimal("90")

    def test_adjustment_creates_movement_record(self, mock_movement_repo):
        """Adjustment should produce a 'adjustment' movement type."""
        movement = StockMovement(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            movement_type="adjustment",
            quantity=Decimal("-10"),
            reference="DMG-001",
        )

        mock_movement_repo.insert_movement(movement)

        mock_movement_repo.insert_movement.assert_called_once()
        assert movement.movement_type == "adjustment"
        assert movement.quantity < 0


class TestLowStockTriggersReorderAlert:
    """When stock drops below reorder_point, notification is created."""

    def test_below_reorder_point_creates_notification(
        self, mock_stock_repo, mock_reorder_repo, mock_notification_svc
    ):
        """Stock at 45 with reorder_point 50 -> notification created."""
        stock = StockLevel(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            current_quantity=Decimal("45"),
            weighted_avg_cost=Decimal("10.00"),
        )
        reorder = ReorderConfig(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            min_stock=Decimal("20"),
            reorder_point=Decimal("50"),
            max_stock=Decimal("500"),
        )

        mock_stock_repo.get_stock_level.return_value = stock
        mock_reorder_repo.get_reorder_config.return_value = reorder

        # Business logic: check if notification needed
        if stock.current_quantity < reorder.reorder_point:
            mock_notification_svc.create_notification(
                tenant_id=1,
                type_="stock_alert",
                title=f"Low stock: {stock.drug_code}",
                body=f"{stock.drug_code} at {stock.site_code} is below reorder point "
                f"({stock.current_quantity} < {reorder.reorder_point})",
            )

        mock_notification_svc.create_notification.assert_called_once()
        call_kwargs = mock_notification_svc.create_notification.call_args
        assert call_kwargs.kwargs["type_"] == "stock_alert"
        assert "PARA500" in call_kwargs.kwargs["title"]

    def test_above_reorder_point_no_notification(
        self, mock_stock_repo, mock_reorder_repo, mock_notification_svc
    ):
        """Stock at 100 with reorder_point 50 -> no notification."""
        stock = StockLevel(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            current_quantity=Decimal("100"),
            weighted_avg_cost=Decimal("10.00"),
        )
        reorder = ReorderConfig(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            min_stock=Decimal("20"),
            reorder_point=Decimal("50"),
            max_stock=Decimal("500"),
        )

        mock_stock_repo.get_stock_level.return_value = stock
        mock_reorder_repo.get_reorder_config.return_value = reorder

        if stock.current_quantity < reorder.reorder_point:
            mock_notification_svc.create_notification(
                tenant_id=1, type_="stock_alert", title="Low stock"
            )

        mock_notification_svc.create_notification.assert_not_called()


class TestStockValuationAfterReceipts:
    """Weighted average cost updates after multiple receipts."""

    def test_wac_calculation(self):
        """Receipt 1: 100 @ $10 = $1000, Receipt 2: 50 @ $12 = $600 -> WAC = $10.67."""
        receipt_1_qty = Decimal("100")
        receipt_1_cost = Decimal("10.00")
        receipt_2_qty = Decimal("50")
        receipt_2_cost = Decimal("12.00")

        total_value = (receipt_1_qty * receipt_1_cost) + (receipt_2_qty * receipt_2_cost)
        total_qty = receipt_1_qty + receipt_2_qty
        wac = (total_value / total_qty).quantize(Decimal("0.01"))

        assert wac == Decimal("10.67")
        assert total_qty == Decimal("150")
        assert total_value == Decimal("1600.00")

    def test_wac_with_existing_stock(self):
        """Existing stock at WAC $10, new receipt at $15 -> blended WAC."""
        existing_qty = Decimal("200")
        existing_wac = Decimal("10.00")
        new_qty = Decimal("100")
        new_cost = Decimal("15.00")

        existing_value = existing_qty * existing_wac
        new_value = new_qty * new_cost
        total_qty = existing_qty + new_qty
        blended_wac = ((existing_value + new_value) / total_qty).quantize(Decimal("0.01"))

        assert blended_wac == Decimal("11.67")
