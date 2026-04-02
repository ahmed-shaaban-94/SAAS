"""Tests for AI-Light API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from datapulse.ai_light.models import AISummary, AnomalyReport, ChangeNarrative
from datapulse.ai_light.service import AILightService
from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_ai_light_service

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


@pytest.fixture()
def mock_service() -> MagicMock:
    svc = MagicMock(spec=AILightService)
    type(svc).is_available = PropertyMock(return_value=True)
    return svc


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_ai_light_service] = lambda: mock_service
    return TestClient(app)


class TestAILightStatus:
    def test_status(self, client: TestClient):
        resp = client.get("/api/v1/ai-light/status")
        assert resp.status_code == 200
        assert resp.json()["available"] is True


class TestAILightSummary:
    def test_summary_not_available(self, client: TestClient, mock_service: MagicMock):
        type(mock_service).is_available = PropertyMock(return_value=False)
        resp = client.get("/api/v1/ai-light/summary")
        assert resp.status_code == 503

    def test_summary_success(self, client: TestClient, mock_service: MagicMock):
        mock_service.generate_summary.return_value = AISummary(
            narrative="Revenue is up 10%.",
            highlights=[],
            period="2025-06-15",
        )
        resp = client.get("/api/v1/ai-light/summary")
        assert resp.status_code == 200

    def test_summary_failure(self, client: TestClient, mock_service: MagicMock):
        mock_service.generate_summary.side_effect = Exception("API timeout")
        resp = client.get("/api/v1/ai-light/summary")
        assert resp.status_code == 502


class TestAILightAnomalies:
    def test_anomalies_success(self, client: TestClient, mock_service: MagicMock):
        mock_service.detect_anomalies.return_value = AnomalyReport(
            anomalies=[], period="2025-01 to 2025-06", total_checked=180
        )
        resp = client.get("/api/v1/ai-light/anomalies")
        assert resp.status_code == 200

    def test_anomalies_failure(self, client: TestClient, mock_service: MagicMock):
        mock_service.detect_anomalies.side_effect = RuntimeError("fail")
        resp = client.get("/api/v1/ai-light/anomalies")
        assert resp.status_code == 502


class TestAILightChanges:
    def test_changes_success(self, client: TestClient, mock_service: MagicMock):
        mock_service.explain_changes.return_value = ChangeNarrative(
            narrative="Sales grew by 5%.",
            deltas=[],
            current_period="2025-06-15",
            previous_period="2025-06-14",
        )
        resp = client.get("/api/v1/ai-light/changes")
        assert resp.status_code == 200

    def test_changes_failure(self, client: TestClient, mock_service: MagicMock):
        mock_service.explain_changes.side_effect = Exception("timeout")
        resp = client.get("/api/v1/ai-light/changes")
        assert resp.status_code == 502
