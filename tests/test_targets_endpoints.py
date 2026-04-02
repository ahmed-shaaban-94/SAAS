"""Tests for targets API endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.targets.models import (
    AlertConfigResponse,
    AlertLogResponse,
    TargetResponse,
    TargetSummary,
    TargetVsActual,
)
from datapulse.targets.service import TargetsService

NOW = datetime(2025, 6, 15, 12, 0, 0)

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


@pytest.fixture()
def mock_targets_service() -> MagicMock:
    return create_autospec(TargetsService, instance=True)


@pytest.fixture()
def client(mock_targets_service: MagicMock) -> TestClient:
    app = create_app()

    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()

    # Override the service dependency
    from datapulse.api.routes.targets import get_targets_service

    app.dependency_overrides[get_targets_service] = lambda: mock_targets_service

    return TestClient(app)


def _target_resp(**overrides) -> TargetResponse:
    base = {
        "id": 1,
        "target_type": "revenue",
        "granularity": "monthly",
        "period": "2025-06",
        "target_value": Decimal("100000"),
        "entity_type": None,
        "entity_key": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return TargetResponse(**base)


def _alert_config_resp(**overrides) -> AlertConfigResponse:
    base = {
        "id": 1,
        "alert_name": "Low revenue",
        "metric": "daily_revenue",
        "condition": "below",
        "threshold": Decimal("5000"),
        "entity_type": None,
        "entity_key": None,
        "enabled": True,
        "notify_channels": ["dashboard"],
        "created_at": NOW,
    }
    base.update(overrides)
    return AlertConfigResponse(**base)


class TestTargetEndpoints:
    def test_create_target(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.create_target.return_value = _target_resp()
        resp = client.post(
            "/api/v1/targets/",
            json={
                "target_type": "revenue",
                "granularity": "monthly",
                "period": "2025-06",
                "target_value": 100000,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == 1

    def test_list_targets(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.list_targets.return_value = [_target_resp()]
        resp = client.get("/api/v1/targets/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "Cache-Control" in resp.headers

    def test_list_targets_with_filters(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.list_targets.return_value = []
        resp = client.get(
            "/api/v1/targets/",
            params={"target_type": "revenue", "granularity": "monthly", "period": "2025"},
        )
        assert resp.status_code == 200
        mock_targets_service.list_targets.assert_called_once_with(
            target_type="revenue", granularity="monthly", period="2025"
        )

    def test_delete_target_found(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.delete_target.return_value = True
        resp = client.delete("/api/v1/targets/1")
        assert resp.status_code == 204

    def test_delete_target_not_found(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.delete_target.return_value = False
        resp = client.delete("/api/v1/targets/1")
        assert resp.status_code == 404

    def test_get_target_summary(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.get_target_summary.return_value = TargetSummary(
            monthly_targets=[
                TargetVsActual(
                    period="2025-01",
                    target_value=Decimal("100000"),
                    actual_value=Decimal("95000"),
                    variance=Decimal("-5000"),
                    achievement_pct=Decimal("95.00"),
                )
            ],
            ytd_target=Decimal("100000"),
            ytd_actual=Decimal("95000"),
            ytd_achievement_pct=Decimal("95.00"),
        )
        resp = client.get("/api/v1/targets/summary", params={"year": 2025})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["monthly_targets"]) == 1


class TestAlertEndpoints:
    def test_list_alert_configs(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.list_alert_configs.return_value = [_alert_config_resp()]
        resp = client.get("/api/v1/targets/alerts/configs")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_alert_config(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.create_alert_config.return_value = _alert_config_resp()
        resp = client.post(
            "/api/v1/targets/alerts/configs",
            json={
                "alert_name": "Low revenue",
                "metric": "daily_revenue",
                "condition": "below",
                "threshold": 5000,
            },
        )
        assert resp.status_code == 201

    def test_toggle_alert_config(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.toggle_alert.return_value = _alert_config_resp(enabled=False)
        resp = client.patch("/api/v1/targets/alerts/configs/1", params={"enabled": False})
        assert resp.status_code == 200

    def test_toggle_alert_config_not_found(
        self, client: TestClient, mock_targets_service: MagicMock
    ):
        mock_targets_service.toggle_alert.return_value = None
        resp = client.patch("/api/v1/targets/alerts/configs/999")
        assert resp.status_code == 404

    def test_get_alert_logs(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.get_active_alerts.return_value = [
            AlertLogResponse(
                id=1,
                alert_config_id=1,
                alert_name="Low revenue",
                fired_at=NOW,
                metric_value=Decimal("3500"),
                threshold_value=Decimal("5000"),
                message="Below threshold",
                acknowledged=False,
            )
        ]
        resp = client.get("/api/v1/targets/alerts/log")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_acknowledge_alert(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.acknowledge_alert.return_value = True
        resp = client.post("/api/v1/targets/alerts/log/1/acknowledge")
        assert resp.status_code == 200
        assert resp.json()["acknowledged"] is True

    def test_acknowledge_alert_not_found(self, client: TestClient, mock_targets_service: MagicMock):
        mock_targets_service.acknowledge_alert.return_value = False
        resp = client.post("/api/v1/targets/alerts/log/999/acknowledge")
        assert resp.status_code == 404
