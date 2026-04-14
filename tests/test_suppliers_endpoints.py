"""API endpoint tests for Suppliers routes."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.billing.plans import get_plan_limits
from datapulse.suppliers.models import SupplierInfo, SupplierList, SupplierPerformance
from datapulse.suppliers.repository import SuppliersRepository
from datapulse.suppliers.service import SuppliersService


def _make_supplier(**overrides) -> SupplierInfo:
    defaults = dict(
        supplier_code="SUP001",
        supplier_name="Test Supplier Ltd",
        payment_terms_days=30,
        lead_time_days=7,
        is_active=True,
    )
    defaults.update(overrides)
    return SupplierInfo(**defaults)


def _make_performance(**overrides) -> SupplierPerformance:
    defaults = dict(
        supplier_code="SUP001",
        supplier_name="Test Supplier Ltd",
        total_orders=5,
        completed_orders=4,
        cancelled_orders=0,
        avg_lead_days=Decimal("6.5"),
        fill_rate=Decimal("0.95"),
        total_spend=Decimal("50000.00"),
        total_received=Decimal("47500.00"),
    )
    defaults.update(overrides)
    return SupplierPerformance(**defaults)


@pytest.fixture()
def supplier_api_client():
    """TestClient with mocked SuppliersService and pro plan limits."""
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user
    from datapulse.api.deps import get_supplier_service, get_tenant_plan_limits

    mock_repo = create_autospec(SuppliersRepository, instance=True)
    mock_svc = SuppliersService(mock_repo)

    app = create_app()
    app.dependency_overrides[get_supplier_service] = lambda: mock_svc
    app.dependency_overrides[get_tenant_plan_limits] = lambda: get_plan_limits("pro")
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user",
        "email": "test@test.com",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["owner"],
        "raw_claims": {},
    }

    client = TestClient(app, raise_server_exceptions=True)
    return client, mock_svc, mock_repo


class TestListSuppliers:
    def test_returns_200(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.list_suppliers.return_value = SupplierList(
            items=[_make_supplier()], total=1, offset=0, limit=50
        )
        resp = client.get("/api/v1/suppliers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["supplier_code"] == "SUP001"

    def test_active_filter(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.list_suppliers.return_value = SupplierList(items=[], total=0, offset=0, limit=50)
        resp = client.get("/api/v1/suppliers?is_active=true")
        assert resp.status_code == 200

    def test_plan_gate_blocks_starter(self, supplier_api_client):
        from datapulse.api.app import create_app
        from datapulse.api.auth import get_current_user
        from datapulse.api.deps import get_supplier_service, get_tenant_plan_limits

        client, svc, repo = supplier_api_client
        app = create_app()
        app.dependency_overrides[get_supplier_service] = lambda: svc
        app.dependency_overrides[get_tenant_plan_limits] = lambda: get_plan_limits("starter")
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": "test", "email": "", "preferred_username": "",
            "tenant_id": "1", "roles": [], "raw_claims": {},
        }
        c = TestClient(app, raise_server_exceptions=True)
        resp = c.get("/api/v1/suppliers")
        assert resp.status_code == 403


class TestCreateSupplier:
    def test_creates_returns_201(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = None   # no existing supplier
        repo.create_supplier.return_value = _make_supplier()

        payload = {
            "supplier_code": "SUP001",
            "supplier_name": "Test Supplier Ltd",
        }
        resp = client.post("/api/v1/suppliers", json=payload)
        assert resp.status_code == 201
        assert resp.json()["supplier_code"] == "SUP001"

    def test_duplicate_code_returns_409(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = _make_supplier()  # already exists

        payload = {
            "supplier_code": "SUP001",
            "supplier_name": "Test Supplier Ltd",
        }
        resp = client.post("/api/v1/suppliers", json=payload)
        assert resp.status_code == 409

    def test_missing_name_returns_422(self, supplier_api_client):
        client, _, _ = supplier_api_client
        resp = client.post("/api/v1/suppliers", json={"supplier_code": "S1"})
        assert resp.status_code == 422


class TestGetSupplier:
    def test_found_returns_200(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = _make_supplier()
        resp = client.get("/api/v1/suppliers/SUP001")
        assert resp.status_code == 200
        assert resp.json()["supplier_name"] == "Test Supplier Ltd"

    def test_not_found_returns_404(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = None
        resp = client.get("/api/v1/suppliers/MISSING")
        assert resp.status_code == 404


class TestUpdateSupplier:
    def test_update_returns_200(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.update_supplier.return_value = _make_supplier(supplier_name="Updated Name")
        resp = client.put("/api/v1/suppliers/SUP001", json={"supplier_name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["supplier_name"] == "Updated Name"

    def test_not_found_returns_404(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.update_supplier.return_value = None
        resp = client.put("/api/v1/suppliers/MISSING", json={"is_active": False})
        assert resp.status_code == 404


class TestGetSupplierPerformance:
    def test_returns_performance(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = _make_supplier()
        repo.get_supplier_performance.return_value = _make_performance()
        resp = client.get("/api/v1/suppliers/SUP001/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_code"] == "SUP001"
        assert data["total_orders"] == 5

    def test_no_orders_returns_zeros(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = _make_supplier()
        repo.get_supplier_performance.return_value = None  # no perf data yet
        resp = client.get("/api/v1/suppliers/SUP001/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] == 0

    def test_not_found_returns_404(self, supplier_api_client):
        client, svc, repo = supplier_api_client
        repo.get_supplier.return_value = None
        resp = client.get("/api/v1/suppliers/MISSING/performance")
        assert resp.status_code == 404
