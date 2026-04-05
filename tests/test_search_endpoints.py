"""Tests for search API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.search import get_search_repo


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
def mock_repo():
    repo = MagicMock()
    repo.search.return_value = {
        "products": [
            {"key": "P1", "name": "Widget", "subtitle": "Electronics", "type": "product"},
        ],
        "customers": [
            {"key": "C1", "name": "Acme", "subtitle": "", "type": "customer"},
        ],
        "staff": [],
    }
    return repo


@pytest.fixture()
def app(mock_user, mock_repo):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_search_repo] = lambda: mock_repo
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


class TestSearchEndpoint:
    def test_search_success(self, client, mock_repo):
        """GET /search?q=test returns grouped results including pages."""
        resp = client.get("/api/v1/search", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "products" in data
        assert "customers" in data
        assert "staff" in data
        assert "pages" in data
        assert len(data["products"]) == 1
        mock_repo.search.assert_called_once_with("test", 10)

    def test_search_empty(self, client, mock_repo):
        """GET /search?q= returns empty results without hitting repo."""
        resp = client.get("/api/v1/search", params={"q": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert data["products"] == []
        assert data["customers"] == []
        assert data["staff"] == []
        assert data["pages"] == []
        mock_repo.search.assert_not_called()

    def test_search_pages_only(self, client, mock_repo):
        """Search matching a page name returns it in the pages list."""
        mock_repo.search.return_value = {
            "products": [],
            "customers": [],
            "staff": [],
        }
        resp = client.get("/api/v1/search", params={"q": "Goals"})
        assert resp.status_code == 200
        data = resp.json()
        pages = data["pages"]
        assert any(p["name"] == "Goals" for p in pages)
        assert all(p["type"] == "page" for p in pages)

    def test_search_with_custom_limit(self, client, mock_repo):
        """Search passes custom limit to repo."""
        resp = client.get("/api/v1/search", params={"q": "test", "limit": 25})
        assert resp.status_code == 200
        mock_repo.search.assert_called_once_with("test", 25)

    def test_search_whitespace_only(self, client, mock_repo):
        """Whitespace-only query returns empty results."""
        resp = client.get("/api/v1/search", params={"q": "   "})
        assert resp.status_code == 200
        data = resp.json()
        assert data["products"] == []
        mock_repo.search.assert_not_called()
