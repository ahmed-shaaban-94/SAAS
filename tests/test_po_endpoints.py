"""API endpoint tests for Purchase Orders routes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.billing.plans import PlanLimits, get_plan_limits
from datapulse.purchase_orders.models import (
    MarginAnalysisList,
    POList,
    PurchaseOrder,
    PurchaseOrderDetail,
)
from datapulse.purchase_orders.repository import PurchaseOrderRepository
from datapulse.purchase_orders.service import PurchaseOrderService


def _make_po(**overrides) -> PurchaseOrder:
    defaults = dict(
        po_number="PO-1-20250115-0001",
        po_date=date(2025, 1, 15),
        supplier_code="SUP001",
        site_code="SITE01",
        status="draft",
        total_ordered_value=Decimal("100.00"),
        total_received_value=Decimal("0"),
        line_count=1,
    )
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def _pro_limits() -> PlanLimits:
    return get_plan_limits("pro")


def _starter_limits() -> PlanLimits:
    return get_plan_limits("starter")


@pytest.fixture()
def po_api_client():
    """TestClient with mocked PO service and pro plan limits."""
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user
    from datapulse.api.deps import get_po_service, get_tenant_plan_limits

    mock_repo = create_autospec(PurchaseOrderRepository, instance=True)
    mock_svc = PurchaseOrderService(mock_repo)

    app = create_app()
    app.dependency_overrides[get_po_service] = lambda: mock_svc
    app.dependency_overrides[get_tenant_plan_limits] = lambda: _pro_limits()
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


class TestListPOs:
    def test_returns_200(self, po_api_client):
        client, svc, repo = po_api_client
        repo.list_pos.return_value = POList(items=[], total=0, offset=0, limit=20)
        resp = client.get("/api/v1/purchase-orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_plan_gate_blocks_starter(self, po_api_client):
        from datapulse.api.deps import get_tenant_plan_limits

        client, svc, repo = po_api_client
        # Override plan to starter
        from datapulse.api.app import create_app
        from datapulse.api.auth import get_current_user
        from datapulse.api.deps import get_po_service

        app = create_app()
        app.dependency_overrides[get_po_service] = lambda: svc
        app.dependency_overrides[get_tenant_plan_limits] = lambda: _starter_limits()
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": "test-user",
            "email": "",
            "preferred_username": "",
            "tenant_id": "1",
            "roles": [],
            "raw_claims": {},
        }
        c = TestClient(app, raise_server_exceptions=True)
        resp = c.get("/api/v1/purchase-orders")
        assert resp.status_code == 403

    def test_status_filter(self, po_api_client):
        client, svc, repo = po_api_client
        repo.list_pos.return_value = POList(items=[], total=0, offset=0, limit=20)
        resp = client.get("/api/v1/purchase-orders?status=draft")
        assert resp.status_code == 200

    def test_invalid_status_returns_422(self, po_api_client):
        client, svc, repo = po_api_client
        resp = client.get("/api/v1/purchase-orders?status=BOGUS")
        assert resp.status_code == 422


class TestCreatePO:
    def test_creates_po_returns_201(self, po_api_client):
        client, svc, repo = po_api_client
        repo.create_po.return_value = _make_po()
        repo.get_po.return_value = _make_po()

        payload = {
            "po_date": "2025-01-15",
            "supplier_code": "SUP001",
            "site_code": "SITE01",
            "lines": [{"drug_code": "D001", "quantity": "10", "unit_price": "5.50"}],
        }
        resp = client.post("/api/v1/purchase-orders", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["po_number"] == "PO-1-20250115-0001"

    def test_missing_lines_returns_422(self, po_api_client):
        client, _, _ = po_api_client
        payload = {
            "po_date": "2025-01-15",
            "supplier_code": "SUP001",
            "site_code": "SITE01",
            "lines": [],
        }
        resp = client.post("/api/v1/purchase-orders", json=payload)
        assert resp.status_code == 422


class TestGetPO:
    def test_found_returns_200(self, po_api_client):

        client, svc, repo = po_api_client
        detail = PurchaseOrderDetail(
            po_number="PO-1-20250115-0001",
            po_date=date(2025, 1, 15),
            supplier_code="SUP001",
            site_code="SITE01",
            status="draft",
            lines=[],
        )
        repo.get_po_detail.return_value = detail
        repo.get_po.return_value = _make_po()
        repo.get_lines.return_value = []
        resp = client.get("/api/v1/purchase-orders/PO-1-20250115-0001")
        assert resp.status_code == 200

    def test_not_found_returns_404(self, po_api_client):
        client, svc, repo = po_api_client
        repo.get_po_detail.return_value = None
        repo.get_po.return_value = None
        resp = client.get("/api/v1/purchase-orders/MISSING")
        assert resp.status_code == 404


class TestReceivePO:
    def test_receive_returns_200(self, po_api_client):
        client, svc, repo = po_api_client
        po_number = "PO-1-20250115-0001"

        repo.get_po.side_effect = [
            _make_po(status="submitted"),
            _make_po(status="received"),
        ]
        repo.get_line_details_map.return_value = {}
        repo.receive_po_lines.return_value = None
        repo.insert_stock_receipts.return_value = 1
        repo.recalculate_po_status.return_value = "received"

        payload = {
            "po_number": po_number,
            "lines": [{"line_number": 1, "received_quantity": "10"}],
        }
        resp = client.post(f"/api/v1/purchase-orders/{po_number}/receive", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "received"

    def test_po_number_mismatch_returns_422(self, po_api_client):
        client, svc, repo = po_api_client
        payload = {
            "po_number": "DIFFERENT",
            "lines": [{"line_number": 1, "received_quantity": "10"}],
        }
        resp = client.post("/api/v1/purchase-orders/PO-001/receive", json=payload)
        assert resp.status_code == 422

    def test_cancelled_po_returns_409(self, po_api_client):
        client, svc, repo = po_api_client
        repo.get_po.return_value = _make_po(status="cancelled")
        payload = {
            "po_number": "PO-1-20250115-0001",
            "lines": [{"line_number": 1, "received_quantity": "5"}],
        }
        resp = client.post("/api/v1/purchase-orders/PO-1-20250115-0001/receive", json=payload)
        assert resp.status_code == 409


class TestCancelPO:
    def test_cancel_returns_200(self, po_api_client):
        client, svc, repo = po_api_client
        repo.cancel_po.return_value = _make_po(status="cancelled")
        resp = client.post("/api/v1/purchase-orders/PO-1-20250115-0001/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_not_found_returns_404(self, po_api_client):
        client, svc, repo = po_api_client
        repo.cancel_po.return_value = None
        repo.get_po.return_value = None
        resp = client.post("/api/v1/purchase-orders/MISSING/cancel")
        assert resp.status_code == 404


class TestGetPOLines:
    def test_returns_lines(self, po_api_client):
        client, svc, repo = po_api_client
        repo.get_po.return_value = _make_po()
        repo.get_lines.return_value = []
        resp = client.get("/api/v1/purchase-orders/PO-1-20250115-0001/lines")
        assert resp.status_code == 200
        data = resp.json()
        assert data["po_number"] == "PO-1-20250115-0001"
        assert data["lines"] == []


class TestMarginAnalysis:
    def test_returns_200(self, po_api_client):
        client, svc, repo = po_api_client
        # repo doesn't have get_margin_analysis — service calls it directly
        # patch the service method
        svc.get_margin_analysis = MagicMock(return_value=MarginAnalysisList(items=[], total=0))
        resp = client.get("/api/v1/margins/analysis")
        assert resp.status_code == 200

    def test_year_month_filter(self, po_api_client):
        client, svc, repo = po_api_client
        svc.get_margin_analysis = MagicMock(
            return_value=MarginAnalysisList(items=[], total=0, year=2025, month=1)
        )
        resp = client.get("/api/v1/margins/analysis?year=2025&month=1")
        assert resp.status_code == 200
        svc.get_margin_analysis.assert_called_once()
        call_kwargs = svc.get_margin_analysis.call_args.kwargs
        assert call_kwargs["year"] == 2025
        assert call_kwargs["month"] == 1
