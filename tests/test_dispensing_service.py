"""Tests for DispensingService — cache hit/miss and delegation to repository."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from datapulse.dispensing.models import (
    DaysOfStock,
    DispenseRate,
    DispensingFilter,
    StockoutRisk,
    VelocityClassification,
)
from datapulse.dispensing.service import DispensingService
from datapulse.inventory.models import StockReconciliation

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def service(mock_repo: MagicMock) -> DispensingService:
    return DispensingService(mock_repo)


def _rate() -> DispenseRate:
    return DispenseRate(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_code="S01",
        site_name="Main",
        active_days=45,
        total_dispensed_90d=Decimal("450"),
        avg_daily_dispense=Decimal("10.0"),
        avg_weekly_dispense=Decimal("70.0"),
        avg_monthly_dispense=Decimal("300.0"),
    )


def _dos() -> DaysOfStock:
    return DaysOfStock(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("100"),
        avg_daily_dispense=Decimal("5.0"),
        days_of_stock=Decimal("20.0"),
        avg_weekly_dispense=Decimal("35.0"),
        avg_monthly_dispense=Decimal("150.0"),
    )


def _velocity() -> VelocityClassification:
    return VelocityClassification(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        drug_category="Analgesics",
        lifecycle_phase="Mature",
        velocity_class="fast_mover",
        avg_daily_dispense=Decimal("10.0"),
        category_avg_daily=Decimal("5.0"),
    )


def _risk() -> StockoutRisk:
    return StockoutRisk(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("5"),
        days_of_stock=Decimal("0.5"),
        avg_daily_dispense=Decimal("10.0"),
        reorder_point=Decimal("20"),
        reorder_lead_days=7,
        min_stock=Decimal("10"),
        risk_level="critical",
        suggested_reorder_qty=Decimal("15"),
    )


# ------------------------------------------------------------------
# Tests — cache miss path (cache_get returns None → hits repo)
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_dispense_rates_cache_miss(service, mock_repo):
    mock_repo.get_dispense_rates.return_value = [_rate()]
    with (
        patch("datapulse.dispensing.service.cache_get", return_value=None),
        patch("datapulse.dispensing.service.cache_set"),
    ):
        result = service.get_dispense_rates(DispensingFilter())
    assert len(result) == 1
    mock_repo.get_dispense_rates.assert_called_once()


@pytest.mark.unit
def test_get_dispense_rates_cache_hit(service, mock_repo):
    cached = [_rate()]
    with patch("datapulse.dispensing.service.cache_get", return_value=cached):
        result = service.get_dispense_rates(DispensingFilter())
    assert result == cached
    mock_repo.get_dispense_rates.assert_not_called()


@pytest.mark.unit
def test_get_days_of_stock_cache_miss(service, mock_repo):
    mock_repo.get_days_of_stock.return_value = [_dos()]
    with (
        patch("datapulse.dispensing.service.cache_get", return_value=None),
        patch("datapulse.dispensing.service.cache_set"),
    ):
        result = service.get_days_of_stock(DispensingFilter())
    assert len(result) == 1
    mock_repo.get_days_of_stock.assert_called_once()


@pytest.mark.unit
def test_get_velocity_cache_miss(service, mock_repo):
    mock_repo.get_velocity.return_value = [_velocity()]
    with (
        patch("datapulse.dispensing.service.cache_get", return_value=None),
        patch("datapulse.dispensing.service.cache_set"),
    ):
        result = service.get_velocity(DispensingFilter())
    assert len(result) == 1
    assert result[0].velocity_class == "fast_mover"


@pytest.mark.unit
def test_get_stockout_risk_cache_miss(service, mock_repo):
    mock_repo.get_stockout_risk.return_value = [_risk()]
    with (
        patch("datapulse.dispensing.service.cache_get", return_value=None),
        patch("datapulse.dispensing.service.cache_set"),
    ):
        result = service.get_stockout_risk(DispensingFilter())
    assert len(result) == 1
    assert result[0].risk_level == "critical"


@pytest.mark.unit
def test_get_reconciliation_cache_miss(service, mock_repo):
    from datetime import date

    recon = StockReconciliation(
        product_key=1,
        site_key=1,
        count_date=date(2025, 3, 1),
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        counted_quantity=Decimal("100"),
        calculated_quantity=Decimal("98"),
        variance=Decimal("-2"),
    )
    mock_repo.get_reconciliation.return_value = [recon]
    with (
        patch("datapulse.dispensing.service.cache_get", return_value=None),
        patch("datapulse.dispensing.service.cache_set"),
    ):
        result = service.get_reconciliation(DispensingFilter())
    assert len(result) == 1
    assert result[0].variance == Decimal("-2")
