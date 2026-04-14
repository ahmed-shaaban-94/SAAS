"""Tests for InventoryRepository — mock session, verify parameterized SQL queries."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.inventory.models import AdjustmentRequest, InventoryFilter
from datapulse.inventory.repository import InventoryRepository


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> InventoryRepository:
    return InventoryRepository(mock_session)


def _mock_rows(*dicts) -> MagicMock:
    """Build a mock that mimics session.execute(...).mappings().all()."""
    mock_execute = MagicMock()
    mock_execute.mappings.return_value.all.return_value = [dict(d) for d in dicts]
    return mock_execute


# ------------------------------------------------------------------
# Stock Levels
# ------------------------------------------------------------------


def test_get_stock_levels_no_filters(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "drug_brand": "Generic",
            "site_key": 1,
            "site_code": "S01",
            "site_name": "Main",
            "current_quantity": Decimal("100"),
            "total_received": Decimal("200"),
            "total_dispensed": Decimal("100"),
            "total_wastage": Decimal("0"),
            "last_movement_date": None,
        }
    )
    result = repo.get_stock_levels(InventoryFilter())
    assert len(result) == 1
    assert result[0].drug_code == "D001"
    mock_session.execute.assert_called_once()


def test_get_stock_levels_with_site_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_stock_levels(InventoryFilter(site_key=2))
    call_args = mock_session.execute.call_args
    params = call_args[0][1]
    assert params["site_key"] == 2


def test_get_stock_levels_with_drug_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_stock_levels(InventoryFilter(drug_code="D001"))
    call_args = mock_session.execute.call_args
    params = call_args[0][1]
    assert params["drug_code"] == "D001"


def test_get_stock_level_by_drug(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "drug_brand": "Generic",
            "site_key": 1,
            "site_code": "S01",
            "site_name": "Main",
            "current_quantity": Decimal("50"),
            "total_received": Decimal("100"),
            "total_dispensed": Decimal("50"),
            "total_wastage": Decimal("0"),
            "last_movement_date": date(2025, 1, 10),
        }
    )
    result = repo.get_stock_level_by_drug("D001", InventoryFilter())
    assert len(result) == 1
    call_args = mock_session.execute.call_args
    params = call_args[0][1]
    assert params["drug_code"] == "D001"


# ------------------------------------------------------------------
# Movements
# ------------------------------------------------------------------


def test_get_movements_no_filters(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "movement_key": 1,
            "movement_date": date(2025, 1, 1),
            "movement_type": "receipt",
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_code": "S01",
            "batch_number": None,
            "quantity": Decimal("100"),
            "unit_cost": Decimal("5.0"),
            "reference": "REF001",
        }
    )
    result = repo.get_movements(InventoryFilter())
    assert len(result) == 1
    assert result[0].movement_type == "receipt"


def test_get_movements_with_type_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_movements(InventoryFilter(movement_type="dispense"))
    params = mock_session.execute.call_args[0][1]
    assert params["movement_type"] == "dispense"


def test_get_movements_by_drug(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_movements_by_drug("D001", InventoryFilter())
    params = mock_session.execute.call_args[0][1]
    assert params["drug_code"] == "D001"


# ------------------------------------------------------------------
# Valuation
# ------------------------------------------------------------------


def test_get_valuation(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_key": 1,
            "site_code": "S01",
            "weighted_avg_cost": Decimal("4.75"),
            "current_quantity": Decimal("200"),
            "stock_value": Decimal("950.00"),
        }
    )
    result = repo.get_valuation(InventoryFilter())
    assert len(result) == 1
    assert result[0].stock_value == Decimal("950.00")


def test_get_valuation_by_drug(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_valuation_by_drug("D001", InventoryFilter())
    params = mock_session.execute.call_args[0][1]
    assert params["drug_code"] == "D001"


# ------------------------------------------------------------------
# Reorder Alerts
# ------------------------------------------------------------------


def test_get_reorder_alerts(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "site_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_code": "S01",
            "current_quantity": Decimal("5"),
            "reorder_point": Decimal("20"),
            "reorder_quantity": Decimal("100"),
        }
    )
    result = repo.get_reorder_alerts(InventoryFilter())
    assert len(result) == 1
    assert result[0].current_quantity == Decimal("5")


# ------------------------------------------------------------------
# Counts
# ------------------------------------------------------------------


def test_get_counts(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "count_key": 1,
            "tenant_id": 1,
            "product_key": 1,
            "site_key": 1,
            "count_date": date(2025, 6, 1),
            "drug_code": "D001",
            "site_code": "S01",
            "batch_number": None,
            "counted_quantity": Decimal("95"),
            "counted_by": "John",
        }
    )
    result = repo.get_counts(InventoryFilter())
    assert len(result) == 1
    assert result[0].counted_quantity == Decimal("95")


def test_get_counts_with_date_range(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_counts(InventoryFilter(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31)))
    params = mock_session.execute.call_args[0][1]
    assert params["start_date"] == date(2025, 1, 1)
    assert params["end_date"] == date(2025, 12, 31)


# ------------------------------------------------------------------
# Reconciliation
# ------------------------------------------------------------------


def test_get_reconciliation(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "site_key": 1,
            "count_date": date(2025, 6, 1),
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_code": "S01",
            "site_name": "Main Pharmacy",
            "counted_quantity": Decimal("95"),
            "calculated_quantity": Decimal("100"),
            "variance": Decimal("-5"),
            "variance_pct": Decimal("-0.05"),
        }
    )
    result = repo.get_reconciliation(InventoryFilter())
    assert len(result) == 1
    assert result[0].variance == Decimal("-5")


# ------------------------------------------------------------------
# Create Adjustment
# ------------------------------------------------------------------


def test_create_adjustment(repo, mock_session):
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="damage",
        quantity=Decimal("-5"),
        reason="Broken packaging",
    )
    repo.create_adjustment(tenant_id=1, request=req)
    mock_session.execute.assert_called_once()
    call_params = mock_session.execute.call_args[0][1]
    assert call_params["drug_code"] == "D001"
    assert call_params["site_code"] == "S01"
    assert call_params["adjustment_type"] == "damage"
    assert call_params["tenant_id"] == 1
    assert call_params["source_file"] == "api"


def test_create_adjustment_with_batch(repo, mock_session):
    req = AdjustmentRequest(
        drug_code="D002",
        site_code="S02",
        adjustment_type="correction",
        quantity=Decimal("10"),
        batch_number="BATCH001",
        reason="Audit correction",
    )
    repo.create_adjustment(tenant_id=2, request=req)
    call_params = mock_session.execute.call_args[0][1]
    assert call_params["batch_number"] == "BATCH001"
    assert call_params["tenant_id"] == 2


def test_create_adjustment_limit_in_filter(repo, mock_session):
    """get_movements_by_drug delegates to get_movements with drug_code injected."""
    mock_session.execute.return_value = _mock_rows()
    repo.get_movements_by_drug("D001", InventoryFilter(limit=25))
    params = mock_session.execute.call_args[0][1]
    assert params["drug_code"] == "D001"
    assert params["limit"] == 25
