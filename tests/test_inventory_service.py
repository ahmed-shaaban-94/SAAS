"""Tests for InventoryService — mock repository, verify caching and business logic."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from datapulse.inventory.models import (
    AdjustmentRequest,
    InventoryFilter,
    ReorderAlert,
    StockLevel,
    StockMovement,
    StockValuation,
)
from datapulse.inventory.repository import InventoryRepository
from datapulse.inventory.service import InventoryService


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(InventoryRepository, instance=True)


@pytest.fixture()
def service(mock_repo: MagicMock) -> InventoryService:
    return InventoryService(mock_repo)


def _stock_level() -> StockLevel:
    return StockLevel(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_key=1,
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("100"),
        total_received=Decimal("200"),
        total_dispensed=Decimal("100"),
        total_wastage=Decimal("0"),
    )


def _movement() -> StockMovement:
    from datetime import date

    return StockMovement(
        movement_key=1,
        movement_date=date(2025, 3, 1),
        movement_type="receipt",
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        quantity=Decimal("50"),
    )


def _alert() -> ReorderAlert:
    return ReorderAlert(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        current_quantity=Decimal("5"),
        reorder_point=Decimal("20"),
        reorder_quantity=Decimal("100"),
    )


# ------------------------------------------------------------------
# Cache miss → repo called → result returned
# ------------------------------------------------------------------


def test_get_stock_levels_calls_repo(service, mock_repo):
    mock_repo.get_stock_levels.return_value = [_stock_level()]
    result = service.get_stock_levels(InventoryFilter())
    assert len(result) == 1
    mock_repo.get_stock_levels.assert_called_once()


def test_get_stock_level_detail_calls_repo(service, mock_repo):
    mock_repo.get_stock_level_by_drug.return_value = [_stock_level()]
    result = service.get_stock_level_detail("D001", InventoryFilter())
    assert result[0].drug_code == "D001"
    mock_repo.get_stock_level_by_drug.assert_called_once_with("D001", InventoryFilter())


def test_get_movements_calls_repo(service, mock_repo):
    mock_repo.get_movements.return_value = [_movement()]
    result = service.get_movements(InventoryFilter())
    assert len(result) == 1
    mock_repo.get_movements.assert_called_once()


def test_get_movements_by_drug_calls_repo(service, mock_repo):
    mock_repo.get_movements_by_drug.return_value = [_movement()]
    result = service.get_movements_by_drug("D001", InventoryFilter())
    assert len(result) == 1
    mock_repo.get_movements_by_drug.assert_called_once_with("D001", InventoryFilter())


def test_get_valuation_calls_repo(service, mock_repo):
    mock_repo.get_valuation.return_value = [
        StockValuation(
            product_key=1,
            drug_code="D001",
            drug_name="Para",
            site_key=1,
            site_code="S01",
            weighted_avg_cost=Decimal("5"),
            current_quantity=Decimal("100"),
            stock_value=Decimal("500"),
        )
    ]
    result = service.get_valuation(InventoryFilter())
    assert len(result) == 1


def test_get_reorder_alerts_calls_repo(service, mock_repo):
    mock_repo.get_reorder_alerts.return_value = [_alert()]
    result = service.get_reorder_alerts(InventoryFilter())
    assert len(result) == 1


def test_get_counts_calls_repo(service, mock_repo):
    from datetime import date

    from datapulse.inventory.models import InventoryCount

    mock_repo.get_counts.return_value = [
        InventoryCount(
            count_key=1,
            tenant_id=1,
            product_key=1,
            site_key=1,
            count_date=date(2025, 6, 1),
            counted_quantity=Decimal("95"),
        )
    ]
    result = service.get_counts(InventoryFilter())
    assert len(result) == 1


def test_get_reconciliation_calls_repo(service, mock_repo):
    from datetime import date

    from datapulse.inventory.models import StockReconciliation

    mock_repo.get_reconciliation.return_value = [
        StockReconciliation(
            product_key=1,
            site_key=1,
            count_date=date(2025, 6, 1),
            drug_code="D001",
            drug_name="Para",
            site_code="S01",
            site_name="Main",
            counted_quantity=Decimal("95"),
            calculated_quantity=Decimal("100"),
            variance=Decimal("-5"),
        )
    ]
    result = service.get_reconciliation(InventoryFilter())
    assert len(result) == 1


# ------------------------------------------------------------------
# Cache hit → repo NOT called
# ------------------------------------------------------------------


def test_get_stock_levels_cache_hit(service, mock_repo):
    cached_data = [_stock_level()]
    with (
        patch("datapulse.inventory.service.cache_get", return_value=cached_data),
        patch("datapulse.inventory.service.cache_set"),
    ):
        result = service.get_stock_levels(InventoryFilter())
    assert result == cached_data
    mock_repo.get_stock_levels.assert_not_called()


def test_get_movements_cache_hit(service, mock_repo):
    cached_data = [_movement()]
    with patch("datapulse.inventory.service.cache_get", return_value=cached_data):
        result = service.get_movements(InventoryFilter())
    assert result == cached_data
    mock_repo.get_movements.assert_not_called()


def test_get_valuation_cache_hit(service, mock_repo):
    with patch("datapulse.inventory.service.cache_get", return_value=[]):
        result = service.get_valuation(InventoryFilter())
    assert result == []
    mock_repo.get_valuation.assert_not_called()


# ------------------------------------------------------------------
# create_adjustment business logic
# ------------------------------------------------------------------


def test_create_adjustment_calls_repo(service, mock_repo):
    mock_repo.get_reorder_alerts.return_value = []
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="damage",
        quantity=Decimal("-5"),
        reason="Test",
    )
    service.create_adjustment(tenant_id=1, request=req)
    mock_repo.create_adjustment.assert_called_once_with(1, req)


def test_create_adjustment_triggers_reorder_check_for_damage(service, mock_repo):
    """Negative/damage adjustments trigger a reorder alert check."""
    mock_repo.get_reorder_alerts.return_value = []
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="damage",
        quantity=Decimal("-10"),
        reason="Broken",
    )
    service.create_adjustment(tenant_id=1, request=req)
    mock_repo.get_reorder_alerts.assert_called_once()


def test_create_adjustment_logs_reorder_warning(service, mock_repo):
    """If post-adjustment stock is below reorder point, warning is logged."""
    mock_repo.get_reorder_alerts.return_value = [_alert()]  # site_code matches
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="shrinkage",
        quantity=Decimal("-20"),
        reason="Theft",
    )
    with patch("datapulse.inventory.service.log") as mock_log:
        service.create_adjustment(tenant_id=1, request=req)
    mock_log.warning.assert_called_once()


def test_create_adjustment_no_reorder_check_for_positive(service, mock_repo):
    """Positive adjustments (correction + qty) do not trigger reorder check."""
    req = AdjustmentRequest(
        drug_code="D001",
        site_code="S01",
        adjustment_type="correction",
        quantity=Decimal("10"),
        reason="Audit",
    )
    service.create_adjustment(tenant_id=1, request=req)
    mock_repo.get_reorder_alerts.assert_not_called()


def test_get_valuation_by_drug_calls_repo(service, mock_repo):
    mock_repo.get_valuation_by_drug.return_value = []
    service.get_valuation_by_drug("D001", InventoryFilter())
    mock_repo.get_valuation_by_drug.assert_called_once_with("D001", InventoryFilter())
