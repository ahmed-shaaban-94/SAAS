"""Tests for expiry API endpoints — plan gating, RBAC, and response shapes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_expiry_service, get_tenant_plan_limits
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.expiry.models import (
    BatchInfo,
    ExpiryAlert,
    ExpiryCalendarDay,
    ExpiryExposureTier,
    ExpirySummary,
    FefoResponse,
)
from datapulse.expiry.service import ExpiryService
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
    permissions={"expiry:read", "expiry:write"},
    sector_ids=[],
    is_admin=True,
)

_PRO_LIMITS = PLAN_LIMITS["pro"]
_STARTER_LIMITS = PLAN_LIMITS["starter"]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_app(service: MagicMock, plan_limits) -> FastAPI:
    from datapulse.api.routes.expiry import router as expiry_router

    app = FastAPI()
    app.include_router(expiry_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_expiry_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: plan_limits
    app.dependency_overrides[get_access_context] = lambda: _ADMIN_CTX
    return app


def _batch_info() -> BatchInfo:
    return BatchInfo(
        batch_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        batch_number="B001",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("100"),
        days_to_expiry=45,
        alert_level="warning",
        computed_status="near_expiry",
    )


def _expiry_alert() -> ExpiryAlert:
    return ExpiryAlert(
        drug_code="D001",
        drug_name="Paracetamol",
        batch_number="B001",
        site_code="S01",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("50"),
        days_to_expiry=15,
        alert_level="critical",
    )


def _expiry_summary() -> ExpirySummary:
    return ExpirySummary(
        site_key=1,
        site_code="S01",
        site_name="Main",
        expiry_bucket="near_expiry",
        batch_count=5,
        total_quantity=Decimal("50"),
        total_value=Decimal("250"),
    )


def _calendar_day() -> ExpiryCalendarDay:
    return ExpiryCalendarDay(
        expiry_date=date(2025, 6, 1),
        batch_count=3,
        total_quantity=Decimal("30"),
        alert_level="warning",
    )


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(ExpiryService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service, _PRO_LIMITS))


@pytest.fixture()
def starter_client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service, _STARTER_LIMITS))


# ------------------------------------------------------------------
# GET /expiry/batches
# ------------------------------------------------------------------


class TestGetBatches:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_batches.return_value = [_batch_info()]
        resp = client.get("/api/v1/expiry/batches")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["drug_code"] == "D001"

    def test_returns_empty_list(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_batches.return_value = []
        resp = client.get("/api/v1/expiry/batches")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/batches")
        assert resp.status_code == 403

    def test_site_code_filter_forwarded(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_batches.return_value = []
        client.get("/api/v1/expiry/batches?site_code=S01")
        filter_arg = mock_service.get_batches.call_args[0][0]
        assert filter_arg.site_code == "S01"


# ------------------------------------------------------------------
# GET /expiry/batches/{drug_code}
# ------------------------------------------------------------------


class TestGetBatchesByDrug:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_batches_by_drug.return_value = [_batch_info()]
        resp = client.get("/api/v1/expiry/batches/D001")
        assert resp.status_code == 200
        mock_service.get_batches_by_drug.assert_called_once()

    def test_drug_code_passed_correctly(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_batches_by_drug.return_value = []
        client.get("/api/v1/expiry/batches/D001")
        assert mock_service.get_batches_by_drug.call_args[0][0] == "D001"

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/batches/D001")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /expiry/alerts
# ------------------------------------------------------------------


class TestGetExpiryAlerts:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_near_expiry.return_value = [_expiry_alert()]
        resp = client.get("/api/v1/expiry/alerts")
        assert resp.status_code == 200
        assert resp.json()[0]["alert_level"] == "critical"

    def test_days_threshold_forwarded(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_near_expiry.return_value = []
        client.get("/api/v1/expiry/alerts?days_threshold=30")
        assert mock_service.get_near_expiry.call_args[0][0] == 30

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/alerts")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /expiry/expired
# ------------------------------------------------------------------


class TestGetExpired:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_expired.return_value = [_expiry_alert()]
        resp = client.get("/api/v1/expiry/expired")
        assert resp.status_code == 200

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/expired")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /expiry/summary
# ------------------------------------------------------------------


class TestGetExpirySummary:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_expiry_summary.return_value = [_expiry_summary()]
        resp = client.get("/api/v1/expiry/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["batch_count"] == 5

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/summary")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /expiry/exposure-summary (issue #506)
# ------------------------------------------------------------------


class TestGetExpiryExposureSummary:
    def _tiers(self) -> list[ExpiryExposureTier]:
        return [
            ExpiryExposureTier(
                tier="30d",
                label="Within 30 days",
                tone="red",
                batch_count=4,
                total_egp=Decimal("48000"),
            ),
            ExpiryExposureTier(
                tier="60d",
                label="31-60 days",
                tone="amber",
                batch_count=5,
                total_egp=Decimal("62000"),
            ),
            ExpiryExposureTier(
                tier="90d",
                label="61-90 days",
                tone="green",
                batch_count=3,
                total_egp=Decimal("32000"),
            ),
        ]

    def test_returns_200_with_three_tiers(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_exposure_tiers.return_value = self._tiers()
        resp = client.get("/api/v1/expiry/exposure-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert [row["tier"] for row in data] == ["30d", "60d", "90d"]
        assert data[0]["tone"] == "red"
        assert data[0]["batch_count"] == 4

    def test_accepts_site_code_filter(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_exposure_tiers.return_value = self._tiers()
        resp = client.get("/api/v1/expiry/exposure-summary?site_code=S01")
        assert resp.status_code == 200
        call = mock_service.get_exposure_tiers.call_args
        assert call.args[0].site_code == "S01"

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/exposure-summary")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# GET /expiry/calendar
# ------------------------------------------------------------------


class TestGetExpiryCalendar:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_expiry_calendar.return_value = [_calendar_day()]
        resp = client.get("/api/v1/expiry/calendar")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.get("/api/v1/expiry/calendar")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# POST /expiry/quarantine
# ------------------------------------------------------------------


class TestQuarantineBatch:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.quarantine_batch.return_value = None
        resp = client.post(
            "/api/v1/expiry/quarantine",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "Contamination",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "quarantined"

    def test_service_called_once(self, client: TestClient, mock_service: MagicMock):
        mock_service.quarantine_batch.return_value = None
        client.post(
            "/api/v1/expiry/quarantine",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "Test",
            },
        )
        mock_service.quarantine_batch.assert_called_once()

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.post(
            "/api/v1/expiry/quarantine",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "Test",
            },
        )
        assert resp.status_code == 403

    def test_missing_reason_returns_422(self, client: TestClient):
        resp = client.post(
            "/api/v1/expiry/quarantine",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
            },
        )
        assert resp.status_code == 422

    def test_reason_too_long_returns_422(self, client: TestClient):
        resp = client.post(
            "/api/v1/expiry/quarantine",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "x" * 501,
            },
        )
        assert resp.status_code == 422


# ------------------------------------------------------------------
# POST /expiry/write-off
# ------------------------------------------------------------------


class TestWriteOffBatch:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.write_off_batch.return_value = None
        resp = client.post(
            "/api/v1/expiry/write-off",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "Expired",
                "quantity": "10",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "written_off"
        assert body["quantity"] == pytest.approx(10.0)

    def test_service_called_once(self, client: TestClient, mock_service: MagicMock):
        mock_service.write_off_batch.return_value = None
        client.post(
            "/api/v1/expiry/write-off",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "Expired",
                "quantity": "5",
            },
        )
        mock_service.write_off_batch.assert_called_once()

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.post(
            "/api/v1/expiry/write-off",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "batch_number": "B001",
                "reason": "Expired",
                "quantity": "5",
            },
        )
        assert resp.status_code == 403


# ------------------------------------------------------------------
# POST /expiry/fefo
# ------------------------------------------------------------------


class TestFefoSelection:
    def test_returns_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.select_fefo.return_value = FefoResponse(
            drug_code="D001",
            site_code="S01",
            required_quantity=Decimal("50"),
            fulfilled=True,
            remaining_unfulfilled=Decimal("0"),
            selections=[
                {
                    "batch_number": "B001",
                    "expiry_date": "2025-06-01",
                    "available_quantity": 100.0,
                    "allocated_quantity": 50.0,
                }
            ],
        )
        resp = client.post(
            "/api/v1/expiry/fefo",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "required_quantity": "50",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["fulfilled"] is True
        assert len(body["selections"]) == 1

    def test_unfulfilled_response(self, client: TestClient, mock_service: MagicMock):
        mock_service.select_fefo.return_value = FefoResponse(
            drug_code="D001",
            site_code="S01",
            required_quantity=Decimal("100"),
            fulfilled=False,
            remaining_unfulfilled=Decimal("70"),
            selections=[],
        )
        resp = client.post(
            "/api/v1/expiry/fefo",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "required_quantity": "100",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["fulfilled"] is False

    def test_starter_plan_returns_403(self, starter_client: TestClient):
        resp = starter_client.post(
            "/api/v1/expiry/fefo",
            json={
                "drug_code": "D001",
                "site_code": "S01",
                "required_quantity": "50",
            },
        )
        assert resp.status_code == 403

    def test_missing_required_quantity_returns_422(self, client: TestClient):
        resp = client.post(
            "/api/v1/expiry/fefo",
            json={"drug_code": "D001", "site_code": "S01"},
        )
        assert resp.status_code == 422
