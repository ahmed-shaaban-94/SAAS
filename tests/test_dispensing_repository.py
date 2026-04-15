"""Tests for DispensingRepository — mock session, verify parameterized SQL."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.dispensing.models import DispensingFilter
from datapulse.dispensing.repository import DispensingRepository


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> DispensingRepository:
    return DispensingRepository(mock_session)


def _mock_rows(*dicts) -> MagicMock:
    """Build a mock that mimics session.execute(...).mappings().all()."""
    mock_execute = MagicMock()
    mock_execute.mappings.return_value.all.return_value = [dict(d) for d in dicts]
    return mock_execute


def _mock_first(row_dict) -> MagicMock:
    mock_execute = MagicMock()
    mock_execute.mappings.return_value.first.return_value = dict(row_dict)
    return mock_execute


# ------------------------------------------------------------------
# Dispense Rates
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_dispense_rates_no_filters(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "site_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "drug_brand": "Generic",
            "site_code": "S01",
            "site_name": "Main",
            "active_days": 45,
            "total_dispensed_90d": Decimal("450"),
            "avg_daily_dispense": Decimal("10.0"),
            "avg_weekly_dispense": Decimal("70.0"),
            "avg_monthly_dispense": Decimal("300.0"),
            "last_dispense_date_key": 20250101,
        }
    )
    result = repo.get_dispense_rates(DispensingFilter())
    assert len(result) == 1
    assert result[0].drug_code == "D001"
    assert result[0].avg_daily_dispense == Decimal("10.0")
    mock_session.execute.assert_called_once()


@pytest.mark.unit
def test_get_dispense_rates_site_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_dispense_rates(DispensingFilter(site_key=2))
    call_args = mock_session.execute.call_args
    params = call_args[0][1]
    assert params["site_key"] == 2


@pytest.mark.unit
def test_get_dispense_rates_drug_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_dispense_rates(DispensingFilter(drug_code="D001"))
    call_args = mock_session.execute.call_args
    params = call_args[0][1]
    assert params["drug_code"] == "D001"


# ------------------------------------------------------------------
# Days of Stock
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_days_of_stock_no_filters(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "site_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_code": "S01",
            "site_name": "Main",
            "current_quantity": Decimal("100"),
            "avg_daily_dispense": Decimal("5.0"),
            "days_of_stock": Decimal("20.0"),
            "avg_weekly_dispense": Decimal("35.0"),
            "avg_monthly_dispense": Decimal("150.0"),
            "last_dispense_date_key": None,
        }
    )
    result = repo.get_days_of_stock(DispensingFilter())
    assert len(result) == 1
    assert result[0].days_of_stock == Decimal("20.0")


@pytest.mark.unit
def test_get_days_of_stock_none_days(repo, mock_session):
    """Products with no dispense history return days_of_stock=None."""
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 2,
            "site_key": 1,
            "drug_code": "D002",
            "drug_name": "NewDrug",
            "site_code": "S01",
            "site_name": "Main",
            "current_quantity": Decimal("50"),
            "avg_daily_dispense": None,
            "days_of_stock": None,
            "avg_weekly_dispense": None,
            "avg_monthly_dispense": None,
            "last_dispense_date_key": None,
        }
    )
    result = repo.get_days_of_stock(DispensingFilter())
    assert result[0].days_of_stock is None
    assert result[0].avg_daily_dispense is None


# ------------------------------------------------------------------
# Velocity
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_velocity_no_filters(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "drug_brand": "Generic",
            "drug_category": "Analgesics",
            "lifecycle_phase": "Mature",
            "velocity_class": "fast_mover",
            "avg_daily_dispense": Decimal("10.0"),
            "category_avg_daily": Decimal("5.0"),
        }
    )
    result = repo.get_velocity(DispensingFilter())
    assert len(result) == 1
    assert result[0].velocity_class == "fast_mover"


@pytest.mark.unit
def test_get_velocity_class_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_velocity(DispensingFilter(velocity_class="dead_stock"))
    params = mock_session.execute.call_args[0][1]
    assert params["velocity_class"] == "dead_stock"


# ------------------------------------------------------------------
# Stockout Risk
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_stockout_risk_no_filters(repo, mock_session):
    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "site_key": 1,
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_code": "S01",
            "site_name": "Main",
            "current_quantity": Decimal("0"),
            "days_of_stock": None,
            "avg_daily_dispense": Decimal("10.0"),
            "reorder_point": Decimal("20"),
            "reorder_lead_days": 7,
            "min_stock": Decimal("10"),
            "risk_level": "stockout",
            "suggested_reorder_qty": Decimal("20"),
        }
    )
    result = repo.get_stockout_risk(DispensingFilter())
    assert len(result) == 1
    assert result[0].risk_level == "stockout"


@pytest.mark.unit
def test_get_stockout_risk_level_filter(repo, mock_session):
    mock_session.execute.return_value = _mock_rows()
    repo.get_stockout_risk(DispensingFilter(risk_level="critical"))
    params = mock_session.execute.call_args[0][1]
    assert params["risk_level"] == "critical"


# ------------------------------------------------------------------
# Reconciliation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_reconciliation_no_filters(repo, mock_session):
    from datetime import date

    mock_session.execute.return_value = _mock_rows(
        {
            "product_key": 1,
            "site_key": 1,
            "count_date": date(2025, 3, 1),
            "drug_code": "D001",
            "drug_name": "Paracetamol",
            "site_code": "S01",
            "site_name": "Main",
            "counted_quantity": Decimal("100"),
            "calculated_quantity": Decimal("98"),
            "variance": Decimal("-2"),
            "variance_pct": Decimal("-2.04"),
        }
    )
    result = repo.get_reconciliation(DispensingFilter())
    assert len(result) == 1
    assert result[0].variance == Decimal("-2")
