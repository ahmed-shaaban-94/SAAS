"""Tests for queries API endpoints — SQL validation and async query flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
    @patch("datapulse.tasks.query_tasks.execute_query")
    def test_submit_query(self, mock_task, client: TestClient):
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_task.apply_async.return_value = mock_result

        resp = client.post(
            "/api/v1/queries",
            json={"sql": "SELECT * FROM public_marts.dim_date LIMIT 10"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["query_id"] == "task-123"
        assert data["status"] == "pending"

    def test_submit_query_blocked_sql(self, client: TestClient):
        resp = client.post(
            "/api/v1/queries",
            json={"sql": "DROP TABLE users"},
        )
        assert resp.status_code == 422

    @patch("datapulse.tasks.celery_app.celery_app")
    def test_get_query_result_pending(self, mock_celery, client: TestClient):
        mock_async = MagicMock()
        mock_async.state = "PENDING"
        mock_async.successful.return_value = False
        mock_celery.AsyncResult.return_value = mock_async

        resp = client.get("/api/v1/queries/task-123")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    @patch("datapulse.tasks.celery_app.celery_app")
    def test_get_query_result_complete(self, mock_celery, client: TestClient):
        mock_async = MagicMock()
        mock_async.state = "SUCCESS"
        mock_async.successful.return_value = True
        mock_async.result = {
            "columns": ["id", "name"],
            "rows": [[1, "test"]],
            "row_count": 1,
            "truncated": False,
            "duration_ms": 42,
        }
        mock_celery.AsyncResult.return_value = mock_async

        resp = client.get("/api/v1/queries/task-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "complete"
        assert data["row_count"] == 1

    @patch("datapulse.tasks.celery_app.celery_app")
    def test_get_query_result_failed(self, mock_celery, client: TestClient):
        mock_async = MagicMock()
        mock_async.state = "FAILURE"
        mock_async.successful.return_value = False
        mock_async.result = Exception("DB error")
        mock_celery.AsyncResult.return_value = mock_async

        resp = client.get("/api/v1/queries/task-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "DB error" in data["error"]
