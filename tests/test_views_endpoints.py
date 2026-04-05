"""Tests for saved views API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.views import get_views_service
from datapulse.views.models import SavedViewResponse

NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


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
    svc = MagicMock()
    sample = SavedViewResponse(
        id=1,
        name="My View",
        page_path="/dashboard",
        filters={"date_range": "30d"},
        is_default=False,
        created_at=NOW,
    )
    svc.list_views.return_value = [sample]
    svc.create_view.return_value = sample
    svc.update_view.return_value = sample
    svc.delete_view.return_value = None
    return svc


@pytest.fixture()
def app(mock_user, mock_service):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_views_service] = lambda: mock_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


class TestListViews:
    def test_list_views(self, client, mock_service):
        """GET /views returns 200 with list of views."""
        resp = client.get("/api/v1/views")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "My View"
        mock_service.list_views.assert_called_once_with("test-user")


class TestCreateView:
    def test_create_view(self, client, mock_service):
        """POST /views returns 201 with created view."""
        resp = client.post(
            "/api/v1/views",
            json={"name": "My View", "page_path": "/dashboard", "filters": {}},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My View"
        mock_service.create_view.assert_called_once()

    def test_create_view_empty_name(self, client):
        """POST /views with empty name returns 422."""
        resp = client.post("/api/v1/views", json={"name": ""})
        assert resp.status_code == 422


class TestUpdateView:
    def test_update_view(self, client, mock_service):
        """PATCH /views/1 returns 200 with updated view."""
        resp = client.patch("/api/v1/views/1", json={"name": "Updated"})
        assert resp.status_code == 200
        mock_service.update_view.assert_called_once()


class TestDeleteView:
    def test_delete_view(self, client, mock_service):
        """DELETE /views/1 returns 204."""
        resp = client.delete("/api/v1/views/1")
        assert resp.status_code == 204
        mock_service.delete_view.assert_called_once()
