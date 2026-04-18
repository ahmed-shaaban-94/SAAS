"""Tests for GET /api/v1/insights/first (Phase 2 Task 3 / #402)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.insights_first import get_first_insight_service
from datapulse.insights_first.models import FirstInsight


@pytest.fixture()
def mock_user():
    return {
        "sub": "test-user",
        "tenant_id": "1",
        "roles": ["admin"],
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "raw_claims": {},
    }


@pytest.fixture()
def mock_service():
    return MagicMock()


@pytest.fixture()
def client(mock_user, mock_service):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_first_insight_service] = lambda: mock_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestGetFirstInsight:
    def test_returns_insight_when_available(self, client, mock_service):
        mock_service.get_first.return_value = FirstInsight(
            kind="top_seller",
            title="Your top seller: Paracetamol 500mg Tab",
            body="drove $10,000 in 30 days",
            action_href="/products",
            confidence=0.72,
        )

        resp = client.get("/api/v1/insights/first")

        assert resp.status_code == 200
        data = resp.json()
        assert data["insight"]["kind"] == "top_seller"
        assert data["insight"]["confidence"] == 0.72
        mock_service.get_first.assert_called_once()

    def test_returns_null_insight_when_none_available(self, client, mock_service):
        mock_service.get_first.return_value = None

        resp = client.get("/api/v1/insights/first")

        assert resp.status_code == 200
        assert resp.json() == {"insight": None}

    def test_forwards_tenant_id_to_service(self, client, mock_service):
        mock_service.get_first.return_value = None

        client.get("/api/v1/insights/first")

        mock_service.get_first.assert_called_once_with(tenant_id=1)
