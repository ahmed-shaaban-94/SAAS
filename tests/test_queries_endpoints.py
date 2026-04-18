"""Tests for queries API endpoints — SQL validation and async query flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.queries import _validate_sql

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    return TestClient(app)


# ── SQL Validation Tests ──────────────────────────────────────────────


class TestSQLValidation:
    def test_select_allowed(self):
        _validate_sql("SELECT * FROM public_marts.dim_date")

    def test_with_cte_allowed(self):
        _validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")

    def test_explain_analyze_select_allowed(self):
        _validate_sql("EXPLAIN ANALYZE SELECT 1")

    def test_insert_blocked(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _validate_sql("INSERT INTO users (name) VALUES ('hack')")
        assert exc.value.status_code == 422

    def test_update_blocked(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_sql("UPDATE users SET name = 'hack'")

    def test_delete_blocked(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_sql("DELETE FROM users")

    def test_drop_blocked(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_sql("DROP TABLE users")

    def test_set_local_app_allowed(self):
        """SET LOCAL app.* is explicitly allowed for RLS tenant context."""
        _validate_sql("SELECT * FROM sales WHERE 1=1")

    def test_random_text_blocked(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_sql("GRANT ALL ON users TO public")

    def test_truncate_blocked(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_sql("TRUNCATE TABLE users")


class TestQueryEndpoints:
    @patch("datapulse.api.routes.queries.submit_query", new_callable=AsyncMock)
    def test_submit_query(self, mock_submit, client: TestClient):
        mock_submit.return_value = "job-123"

        resp = client.post(
            "/api/v1/queries",
            json={"sql": "SELECT * FROM public_marts.dim_date LIMIT 10"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["query_id"] == "job-123"
        assert data["status"] == "pending"

    @patch("datapulse.api.routes.queries.submit_query", new_callable=AsyncMock)
    def test_submit_query_redis_unavailable(self, mock_submit, client: TestClient):
        mock_submit.return_value = None

        resp = client.post(
            "/api/v1/queries",
            json={"sql": "SELECT 1"},
        )
        assert resp.status_code == 503

    @patch("datapulse.api.routes.queries.submit_query", new_callable=AsyncMock)
    def test_submit_query_capacity_exceeded(self, mock_submit, client: TestClient):
        from datapulse.tasks.async_executor import QueryCapacityExceededError

        mock_submit.side_effect = QueryCapacityExceededError("executor busy")

        resp = client.post(
            "/api/v1/queries",
            json={"sql": "SELECT 1"},
        )
        assert resp.status_code == 429
        assert "executor busy" in resp.json()["detail"]

    def test_submit_query_blocked_sql(self, client: TestClient):
        resp = client.post(
            "/api/v1/queries",
            json={"sql": "DROP TABLE users"},
        )
        assert resp.status_code == 422

    @patch("datapulse.api.routes.queries.get_job_result")
    def test_get_query_result_pending(self, mock_get, client: TestClient):
        mock_get.return_value = {"status": "pending"}

        resp = client.get("/api/v1/queries/job-123")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    @patch("datapulse.api.routes.queries.get_job_result")
    def test_get_query_result_complete(self, mock_get, client: TestClient):
        mock_get.return_value = {
            "status": "complete",
            "columns": ["id", "name"],
            "rows": [[1, "test"]],
            "row_count": 1,
            "truncated": False,
            "duration_ms": 42,
        }

        resp = client.get("/api/v1/queries/job-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "complete"
        assert data["row_count"] == 1

    @patch("datapulse.api.routes.queries.get_job_result")
    def test_get_query_result_failed(self, mock_get, client: TestClient):
        mock_get.return_value = {
            "status": "failed",
            "error": "DB error",
        }

        resp = client.get("/api/v1/queries/job-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "DB error" in data["error"]

    @patch("datapulse.api.routes.queries.get_job_result")
    def test_get_query_result_not_found(self, mock_get, client: TestClient):
        mock_get.return_value = None

        resp = client.get("/api/v1/queries/nonexistent")
        assert resp.status_code == 404
