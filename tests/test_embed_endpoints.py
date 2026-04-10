"""Tests for embed API endpoints (auth_router + public_router)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient


def _make_embed_client():
    """Build a TestClient with embed-related dependencies mocked."""
    from datapulse.api import deps
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }

    mock_session = MagicMock()
    app = create_app()
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    return client


class TestGenerateEmbedToken:
    @patch("datapulse.api.routes.embed.create_embed_token", return_value="fake-token-abc")
    def test_generate_token_success(self, mock_create):
        client = _make_embed_client()
        resp = client.post(
            "/api/v1/embed/token",
            json={"resource_type": "explore", "resource_id": "test", "expires_hours": 4},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == "fake-token-abc"
        assert data["expires_hours"] == 4

    @patch("datapulse.api.routes.embed.create_embed_token", return_value="tok")
    def test_generate_token_defaults(self, mock_create):
        client = _make_embed_client()
        resp = client.post("/api/v1/embed/token", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["expires_hours"] == 8


class TestEmbedQuery:
    @patch("datapulse.api.routes.embed.get_session_factory")
    @patch("datapulse.api.routes.embed.validate_embed_token")
    @patch("datapulse.api.routes.embed.build_catalog")
    @patch("datapulse.api.routes.embed.build_sql")
    def test_embed_query_success(
        self, mock_build_sql, mock_build_catalog, mock_validate, mock_factory
    ):
        client = _make_embed_client()
        mock_validate.return_value = {"tenant_id": "1"}

        mock_catalog = MagicMock()
        mock_build_catalog.return_value = mock_catalog
        mock_build_sql.return_value = ("SELECT 1 AS val", {})

        mock_session = MagicMock()
        mock_factory.return_value = lambda: mock_session
        mock_result = MagicMock()
        mock_result.keys.return_value = ["val"]
        mock_result.__iter__ = lambda self: iter([(1,)])
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/embed/fake-token/query",
            json={"model": "fct_sales", "dimensions": ["date_key"], "metrics": ["total_sales"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_count"] == 1
        assert data["columns"] == ["val"]

    @patch("datapulse.api.routes.embed.validate_embed_token")
    def test_embed_query_invalid_token(self, mock_validate):
        client = _make_embed_client()
        mock_validate.side_effect = pyjwt.InvalidTokenError("bad token")

        resp = client.post(
            "/api/v1/embed/bad-token/query",
            json={"model": "fct_sales", "dimensions": [], "metrics": []},
        )
        assert resp.status_code == 401
        assert "Invalid or expired" in resp.json()["detail"]

    @patch("datapulse.api.routes.embed.get_session_factory")
    @patch("datapulse.api.routes.embed.validate_embed_token")
    @patch("datapulse.api.routes.embed.build_catalog")
    @patch("datapulse.api.routes.embed.build_sql")
    def test_embed_query_value_error(
        self, mock_build_sql, mock_build_catalog, mock_validate, mock_factory
    ):
        client = _make_embed_client()
        mock_validate.return_value = {"tenant_id": "1"}
        mock_build_catalog.return_value = MagicMock()
        mock_build_sql.side_effect = ValueError("Unknown model")

        mock_session = MagicMock()
        mock_factory.return_value = lambda: mock_session

        resp = client.post(
            "/api/v1/embed/tok/query",
            json={"model": "bad_model", "dimensions": [], "metrics": []},
        )
        assert resp.status_code == 422

    @patch("datapulse.api.routes.embed.get_session_factory")
    @patch("datapulse.api.routes.embed.validate_embed_token")
    @patch("datapulse.api.routes.embed.build_catalog")
    @patch("datapulse.api.routes.embed.build_sql")
    def test_embed_query_execution_error(
        self, mock_build_sql, mock_build_catalog, mock_validate, mock_factory
    ):
        client = _make_embed_client()
        mock_validate.return_value = {"tenant_id": "1"}
        mock_build_catalog.return_value = MagicMock()
        mock_build_sql.return_value = ("SELECT 1", {})

        mock_session = MagicMock()
        mock_factory.return_value = lambda: mock_session
        # execute is called for SET LOCAL (succeeds), then for the query (fails)
        call_count = {"n": 0}

        def _side_effect(*a, **kw):
            call_count["n"] += 1
            if call_count["n"] > 1:
                raise OSError("DB down")
            return MagicMock()

        mock_session.execute.side_effect = _side_effect

        resp = client.post(
            "/api/v1/embed/tok/query",
            json={"model": "fct_sales", "dimensions": [], "metrics": []},
        )
        assert resp.status_code == 500
        assert "Query execution failed" in resp.json()["detail"]

    @patch("datapulse.api.routes.embed.get_session_factory")
    @patch("datapulse.api.routes.embed.validate_embed_token")
    @patch("datapulse.api.routes.embed.build_catalog")
    @patch("datapulse.api.routes.embed.build_sql")
    def test_embed_query_truncated(
        self, mock_build_sql, mock_build_catalog, mock_validate, mock_factory
    ):
        """Test that results are truncated when exceeding the limit."""
        client = _make_embed_client()
        mock_validate.return_value = {"tenant_id": "1"}
        mock_build_catalog.return_value = MagicMock()
        mock_build_sql.return_value = ("SELECT 1", {})

        mock_session = MagicMock()
        mock_factory.return_value = lambda: mock_session
        # Return more rows than limit (default 500)
        rows = [(i,) for i in range(600)]
        mock_result = MagicMock()
        mock_result.keys.return_value = ["val"]
        mock_result.__iter__ = lambda self: iter(rows)
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/embed/tok/query",
            json={"model": "m", "dimensions": [], "metrics": [], "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["truncated"] is True
        assert data["row_count"] == 10


class TestSerialise:
    def test_serialise_types(self):
        from datetime import date
        from decimal import Decimal

        from datapulse.api.routes.embed import _serialise

        assert _serialise(None) is None
        assert _serialise(Decimal("10.5")) == 10.5
        assert _serialise(datetime(2025, 1, 1, 12, 0)) == "2025-01-01T12:00:00"
        assert _serialise(date(2025, 1, 1)) == "2025-01-01"
        assert _serialise(42) == 42
        assert _serialise("hello") == "hello"
        assert _serialise(True) is True
        assert _serialise(3.14) == 3.14
        # Fallback to str
        assert _serialise(object()) is not None
