"""Tests for inventory Pydantic models — validation and immutability."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datapulse.inventory.models import (
    AdjustmentRequest,
    InventoryFilter,
    ReorderAlert,
    StockLevel,
    StockMovement,
    StockReconciliation,
    StockValuation,
)

# ------------------------------------------------------------------
# StockLevel
# ------------------------------------------------------------------


def test_stock_level_creation():
    sl = StockLevel(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_key=1,
        site_code="S01",
        site_name="Main Pharmacy",
        current_quantity=Decimal("100"),
        total_received=Decimal("200"),
        total_dispensed=Decimal("100"),
        total_wastage=Decimal("0"),
    )
    assert sl.drug_code == "D001"
    assert sl.current_quantity == Decimal("100")
    assert sl.last_movement_date is None


def test_stock_level_with_movement_date():
    sl = StockLevel(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_key=1,
        site_code="S01",
        site_name="Main Pharmacy",
        current_quantity=Decimal("50"),
        total_received=Decimal("100"),
        total_dispensed=Decimal("50"),
        total_wastage=Decimal("0"),
        last_movement_date=date(2025, 1, 15),
    )
    assert sl.last_movement_date == date(2025, 1, 15)


def test_stock_level_frozen():
    sl = StockLevel(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_key=1,
        site_code="S01",
        site_name="Main Pharmacy",
        current_quantity=Decimal("100"),
        total_received=Decimal("100"),
        total_dispensed=Decimal("0"),
        total_wastage=Decimal("0"),
    )
    with pytest.raises(ValidationError):
        sl.drug_code = "D999"


# ------------------------------------------------------------------
# StockMovement
# ------------------------------------------------------------------


def test_stock_movement_creation():
    m = StockMovement(
        movement_key=12345,
        movement_date=date(2025, 3, 10),
        movement_type="receipt",
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        quantity=Decimal("100"),
    )
    assert m.movement_type == "receipt"
    assert m.batch_number is None
    assert m.unit_cost is None


def test_stock_movement_with_optional_fields():
    m = StockMovement(
        movement_key=9999,
        movement_date=date(2025, 3, 10),
        movement_type="dispense",
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        batch_number="B001",
        quantity=Decimal("-10"),
        unit_cost=Decimal("5.50"),
        reference="INV-001",
    )
    assert m.batch_number == "B001"
    assert m.reference == "INV-001"


def test_stock_movement_frozen():
    m = StockMovement(
        movement_key=1,
        movement_date=date(2025, 1, 1),
        movement_type="receipt",
        drug_code="D001",
        drug_name="Drug",
        site_code="S01",
        quantity=Decimal("10"),
    )
    with pytest.raises(ValidationError):
        m.movement_type = "dispense"


# ------------------------------------------------------------------
# StockValuation
# ------------------------------------------------------------------


def test_stock_valuation_creation():
    v = StockValuation(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_key=1,
        site_code="S01",
        weighted_avg_cost=Decimal("4.75"),
        current_quantity=Decimal("200"),
        stock_value=Decimal("950.00"),
    )
    assert v.stock_value == Decimal("950.00")


def test_stock_valuation_frozen():
    v = StockValuation(
        product_key=1,
        drug_code="D001",
        drug_name="Drug",
        site_key=1,
        site_code="S01",
        weighted_avg_cost=Decimal("5"),
        current_quantity=Decimal("100"),
        stock_value=Decimal("500"),
    )
    with pytest.raises(ValidationError):
        v.stock_value = Decimal("9999")


# ------------------------------------------------------------------
# InventoryFilter
# ------------------------------------------------------------------


def test_inventory_filter_defaults():
    f = InventoryFilter()
    assert f.limit == 50
    assert f.site_key is None
    assert f.drug_code is None
    assert f.movement_type is None
    assert f.start_date is None
    assert f.end_date is None


def test_inventory_filter_limit_bounds():
    with pytest.raises(ValidationError):
        InventoryFilter(limit=0)
    with pytest.raises(ValidationError):
        InventoryFilter(limit=501)


def test_inventory_filter_with_values():
    f = InventoryFilter(
        site_key=2,
        drug_code="D001",
        movement_type="receipt",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        limit=100,
    )
    assert f.site_key == 2
    assert f.drug_code == "D001"
    assert f.limit == 100


def test_inventory_filter_drug_code_max_length():
    with pytest.raises(ValidationError):
        InventoryFilter(drug_code="x" * 101)


def test_inventory_filter_frozen():
    f = InventoryFilter(limit=10)
    with pytest.raises(ValidationError):
        f.limit = 20


# ------------------------------------------------------------------
# AdjustmentRequest
# ------------------------------------------------------------------


def test_adjustment_request_creation():
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="damage",
        quantity=Decimal("-5"),
        reason="Broken packaging",
    )
    assert req.adjustment_type == "damage"
    assert req.batch_number is None


def test_adjustment_request_with_batch():
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="correction",
        quantity=Decimal("10"),
        batch_number="B002",
        reason="Count correction after audit",
    )
    assert req.batch_number == "B002"


def test_adjustment_request_frozen():
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="damage",
        quantity=Decimal("-1"),
        reason="Test",
    )
    with pytest.raises(ValidationError):
        req.drug_code = "D999"


def test_adjustment_request_drug_code_max_length():
    with pytest.raises(ValidationError):
        AdjustmentRequest(
            drug_code="x" * 101,
            site_code="S01",
            adjustment_type="damage",
            quantity=Decimal("-1"),
            reason="Test",
        )


def test_adjustment_request_reason_max_length():
    with pytest.raises(ValidationError):
        AdjustmentRequest(
            drug_code="D001",
            site_code="S01",
            adjustment_type="damage",
            quantity=Decimal("-1"),
            reason="x" * 501,
        )


# ------------------------------------------------------------------
# StockReconciliation
# ------------------------------------------------------------------


def test_stock_reconciliation_creation():
    r = StockReconciliation(
        product_key=1,
        site_key=1,
        count_date=date(2025, 6, 1),
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main Pharmacy",
        counted_quantity=Decimal("95"),
        calculated_quantity=Decimal("100"),
        variance=Decimal("-5"),
        variance_pct=Decimal("-0.05"),
    )
    assert r.variance == Decimal("-5")
    assert r.variance_pct == Decimal("-0.05")


def test_stock_reconciliation_null_variance_pct():
    r = StockReconciliation(
        product_key=1,
        site_key=1,
        count_date=date(2025, 6, 1),
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main Pharmacy",
        counted_quantity=Decimal("0"),
        calculated_quantity=Decimal("0"),
        variance=Decimal("0"),
        variance_pct=None,
    )
    assert r.variance_pct is None


# ------------------------------------------------------------------
# ReorderAlert
# ------------------------------------------------------------------


def test_reorder_alert_creation():
    a = ReorderAlert(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        current_quantity=Decimal("5"),
        reorder_point=Decimal("20"),
        reorder_quantity=Decimal("100"),
    )
    assert a.current_quantity == Decimal("5")
    assert a.reorder_point == Decimal("20")
