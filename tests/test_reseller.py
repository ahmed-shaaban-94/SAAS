"""Tests for reseller module — models, service, endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.reseller.models import (
    CommissionResponse,
    PayoutResponse,
    ResellerCreate,
    ResellerDashboard,
    ResellerResponse,
    ResellerTenantResponse,
)
from datapulse.reseller.repository import ResellerRepository
from datapulse.reseller.service import ResellerService

NOW = datetime(2025, 6, 15, 12, 0, 0)

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["owner"],
    "raw_claims": {},
}


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(ResellerRepository, instance=True)


@pytest.fixture()
def service(mock_repo: MagicMock) -> ResellerService:
    return ResellerService(mock_repo)


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(ResellerService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()

    from datapulse.api.routes.reseller import get_reseller_service
    app.dependency_overrides[get_reseller_service] = lambda: mock_service

    return TestClient(app)


def _reseller(**overrides) -> ResellerResponse:
    base = {
        "reseller_id": 1,
        "name": "Partner Co",
        "contact_email": "partner@co.com",
        "commission_pct": Decimal("20.00"),
        "is_active": True,
        "tenant_count": 3,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return ResellerResponse(**base)


class TestModels:
    def test_reseller_create(self):
        r = ResellerCreate(name="Test", contact_email="t@t.com")
        assert r.commission_pct == Decimal("20.00")

    def test_reseller_response_frozen(self):
        r = _reseller()
        with pytest.raises((TypeError, AttributeError, ValidationError)):
            r.name = "Other"

    def test_reseller_dashboard(self):
        d = ResellerDashboard(reseller=_reseller())
        assert d.total_mrr == Decimal("0")
        assert len(d.tenants) == 0

    def test_commission_response(self):
        c = CommissionResponse(
            id=1, reseller_id=1, tenant_id=1, period="2025-06",
            mrr_amount=Decimal("49"), commission_amount=Decimal("9.80"),
            commission_pct=Decimal("20"), status="pending",
        )
        assert c.status == "pending"

    def test_payout_response(self):
        p = PayoutResponse(
            id=1, reseller_id=1, amount=Decimal("100"), status="completed",
            period_from="2025-01", period_to="2025-06", created_at=NOW,
        )
        assert p.currency == "USD"


class TestResellerService:
    def test_create_reseller(self, service, mock_repo):
        mock_repo.create_reseller.return_value = _reseller()
        result = service.create_reseller(ResellerCreate(name="Test", contact_email="t@t.com"))
        assert result.name == "Partner Co"

    def test_get_reseller_found(self, service, mock_repo):
        mock_repo.get_reseller.return_value = _reseller()
        result = service.get_reseller(1)
        assert result.reseller_id == 1

    def test_get_reseller_not_found(self, service, mock_repo):
        mock_repo.get_reseller.return_value = None
        with pytest.raises(ValueError, match="not found"):
            service.get_reseller(999)

    def test_list_resellers(self, service, mock_repo):
        mock_repo.list_resellers.return_value = [_reseller()]
        result = service.list_resellers()
        assert len(result) == 1

    def test_get_dashboard(self, service, mock_repo):
        mock_repo.get_reseller.return_value = _reseller()
        mock_repo.get_reseller_tenants.return_value = [
            ResellerTenantResponse(tenant_id=1, tenant_name="Acme", plan="pro"),
        ]
        mock_repo.get_commissions.return_value = [
            CommissionResponse(
                id=1, reseller_id=1, tenant_id=1, period="2025-06",
                mrr_amount=Decimal("49"), commission_amount=Decimal("9.80"),
                commission_pct=Decimal("20"), status="pending",
            ),
        ]
        mock_repo.get_pending_payout_total.return_value = Decimal("9.80")

        result = service.get_dashboard(1)
        assert len(result.tenants) == 1
        assert result.pending_payout == Decimal("9.80")

    def test_get_commissions(self, service, mock_repo):
        mock_repo.get_commissions.return_value = []
        result = service.get_commissions(1)
        assert result == []

    def test_get_payouts(self, service, mock_repo):
        mock_repo.get_payouts.return_value = []
        result = service.get_payouts(1)
        assert result == []


class TestResellerEndpoints:
    def test_list_resellers(self, client, mock_service):
        mock_service.list_resellers.return_value = [_reseller()]
        resp = client.get("/api/v1/reseller/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_reseller(self, client, mock_service):
        mock_service.create_reseller.return_value = _reseller()
        resp = client.post("/api/v1/reseller/", json={
            "name": "Partner Co", "contact_email": "p@co.com",
        })
        assert resp.status_code == 201

    def test_get_dashboard(self, client, mock_service):
        mock_service.get_dashboard.return_value = ResellerDashboard(reseller=_reseller())
        resp = client.get("/api/v1/reseller/1/dashboard")
        assert resp.status_code == 200
        assert resp.json()["reseller"]["name"] == "Partner Co"

    def test_get_dashboard_not_found(self, client, mock_service):
        mock_service.get_dashboard.side_effect = ValueError("not found")
        resp = client.get("/api/v1/reseller/999/dashboard")
        assert resp.status_code == 404

    def test_get_tenants(self, client, mock_service):
        mock_service.get_tenants.return_value = [
            ResellerTenantResponse(tenant_id=1, tenant_name="Acme", plan="pro"),
        ]
        resp = client.get("/api/v1/reseller/1/tenants")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_commissions(self, client, mock_service):
        mock_service.get_commissions.return_value = []
        resp = client.get("/api/v1/reseller/1/commissions")
        assert resp.status_code == 200

    def test_get_payouts(self, client, mock_service):
        mock_service.get_payouts.return_value = []
        resp = client.get("/api/v1/reseller/1/payouts")
        assert resp.status_code == 200
