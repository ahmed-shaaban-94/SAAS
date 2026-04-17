"""Tests for inventory API endpoints — plan gating, RBAC, and response shapes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_inventory_service, get_tenant_plan_limits
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.inventory.models import (
    InventoryCount,
    InventoryFilter,
    ReorderAlert,
    StockLevel,
    StockMovement,
    StockReconciliation,
    StockValuation,
)
from datapulse.inventory.service import InventoryService
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}

_ADMIN_CTX = AccessContext(
    member_id=1,
    tenant_id=1,
    user_id="test-user",
    role_key="owner",
    permissions={"inventory:read", "inventory:write"},
    sector_ids=[],
    is_admin=True,
)

_PRO_LIMITS = PLAN_LIMITS["pro"]
_STARTER_LIMITS = PLAN_LIMITS["starter"]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_app(service: MagicMock, plan_limits) -> FastAPI:
    """Build a minimal FastAPI app with only the inventory router mounted."""
    from datapulse.api.routes.inventory import router as inventory_router

    app = FastAPI()
    app.include_router(inventory_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_inventory_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: plan_limits
    app.dependency_overrides[get_access_context] = lambda: _ADMIN_CTX
    return app


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
    return StockMovement(
        movement_key=1,
        movement_date=date(2025, 3, 1),
        movement_type="receipt",
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        quantity=Decimal("50"),
    )


def _valuation() -> StockValuation:
    return StockValuation(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_key=1,
        site_code="S01",
        weighted_avg_cost=Decimal("5"),
        current_quantity=Decimal("100"),
        stock_value=Decimal("500"),
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


def _count() -> InventoryCount:
    return InventoryCount(
        count_key=1,
        tenant_id=1,
        product_key=1,
        site_key=1,
        count_date=date(2025, 6, 1),
        counted_quantity=Decimal("95"),
    )


def _reconciliation() -> StockReconciliation:
    return StockReconciliation(
        product_key=1,
        site_key=1,
        count_date=date(2025, 6, 1),
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        counted_quantity=Decimal("95"),
        calculated_quantity=Decimal("100"),
        variance=Decimal("-5"),
    )


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(InventoryService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service, _PRO_LIMITS))


@pytest.fixture()
def starter_client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service, _STARTER_LIMITS))


# ------------------------------------------------------------------
# GET /api/v1/inventory/stock-levels
# ------------------------------------------------------------------


class TestStockLevels:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_stock_levels.return_value = [_stock_level()]
        resp = client.get("/api/v1/inventory/stock-levels")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["drug_code"] == "D001"

    def test_site_filter_forwarded(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_stock_levels.return_value = []
        client.get("/api/v1/inventory/stock-levels?site_key=2")
        called_filter: InventoryFilter = mock_service.get_stock_levels.call_args[0][0]
        assert called_filter.site_key == 2

    def test_limit_filter_forwarded(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_stock_levels.return_value = []
        client.get("/api/v1/inventory/stock-levels?limit=25")
        called_filter = mock_service.get_stock_levels.call_args[0][0]
        assert called_filter.limit == 25

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/inventory/stock-levels")
        assert resp.status_code == 403

    def test_by_drug_code(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_stock_level_detail.return_value = [_stock_level()]
        resp = client.get("/api/v1/inventory/stock-levels/D001")
        assert resp.status_code == 200
        mock_service.get_stock_level_detail.assert_called_once()

    def test_drug_code_passed_correctly(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_stock_level_detail.return_value = [_stock_level()]
        client.get("/api/v1/inventory/stock-levels/D001")
        call_args = mock_service.get_stock_level_detail.call_args[0]
        assert call_args[0] == "D001"


# ------------------------------------------------------------------
# GET /api/v1/inventory/movements
# ------------------------------------------------------------------


class TestMovements:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_movements.return_value = [_movement()]
        resp = client.get("/api/v1/inventory/movements")
        assert resp.status_code == 200
        assert resp.json()[0]["movement_type"] == "receipt"

    def test_by_drug_code(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_movements_by_drug.return_value = [_movement()]
        resp = client.get("/api/v1/inventory/movements/D001")
        assert resp.status_code == 200
        mock_service.get_movements_by_drug.assert_called_once()

    def test_drug_code_passed_to_service(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_movements_by_drug.return_value = []
        client.get("/api/v1/inventory/movements/D001")
        assert mock_service.get_movements_by_drug.call_args[0][0] == "D001"

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/inventory/movements")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /api/v1/inventory/valuation
# ------------------------------------------------------------------


class TestValuation:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_valuation.return_value = [_valuation()]
        resp = client.get("/api/v1/inventory/valuation")
        assert resp.status_code == 200
        assert resp.json()[0]["drug_code"] == "D001"

    def test_by_drug_code(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_valuation_by_drug.return_value = [_valuation()]
        resp = client.get("/api/v1/inventory/valuation/D001")
        assert resp.status_code == 200
        mock_service.get_valuation_by_drug.assert_called_once()

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/inventory/valuation")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /api/v1/inventory/alerts/reorder
# ------------------------------------------------------------------


class TestReorderAlerts:
    def test_returns_200_with_pro_plan(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_reorder_alerts.return_value = [_alert()]
        resp = client.get("/api/v1/inventory/alerts/reorder")
        assert resp.status_code == 200
        assert resp.json()[0]["drug_code"] == "D001"

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/inventory/alerts/reorder")
        assert resp.status_code == 403

    def test_no_stock_alerts_returns_403(self, mock_service: MagicMock):
        """inventory_management=True but stock_alerts=False → 403."""
        from dataclasses import replace

        no_alerts = replace(_PRO_LIMITS, stock_alerts=False)
        tc = TestClient(_make_app(mock_service, no_alerts))
        resp = tc.get("/api/v1/inventory/alerts/reorder")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# POST /api/v1/inventory/adjustments
# ------------------------------------------------------------------


class TestAdjustments:
    def test_create_returns_201(self, client: TestClient, mock_service: MagicMock):
        mock_service.create_adjustment.return_value = None
        resp = client.post(
            "/api/v1/inventory/adjustments",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "adjustment_type": "damage",
                "quantity": "-5",
                "reason": "Broken packaging",
            },
        )
        assert resp.status_code == 201
        assert resp.json() == {"status": "created"}

    def test_service_called_once(self, client: TestClient, mock_service: MagicMock):
        mock_service.create_adjustment.return_value = None
        client.post(
            "/api/v1/inventory/adjustments",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "adjustment_type": "correction",
                "quantity": "10",
                "reason": "Audit fix",
            },
        )
        mock_service.create_adjustment.assert_called_once()

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.post(
            "/api/v1/inventory/adjustments",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "adjustment_type": "damage",
                "quantity": "-1",
                "reason": "Test",
            },
        )
        assert resp.status_code == 403

    def test_invalid_reason_too_long_returns_422(self, client: TestClient):
        resp = client.post(
            "/api/v1/inventory/adjustments",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "adjustment_type": "damage",
                "quantity": "-1",
                "reason": "x" * 501,
            },
        )
        assert resp.status_code == 422


# ------------------------------------------------------------------
# GET /api/v1/inventory/counts
# ------------------------------------------------------------------


class TestCounts:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_counts.return_value = [_count()]
        resp = client.get("/api/v1/inventory/counts")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/inventory/counts")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /api/v1/inventory/reconciliation
# ------------------------------------------------------------------


class TestReconciliation:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_reconciliation.return_value = [_reconciliation()]
        resp = client.get("/api/v1/inventory/reconciliation")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["variance"] == -5.0

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/inventory/reconciliation")
        assert resp.status_code == 403
