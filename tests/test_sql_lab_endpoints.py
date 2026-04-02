"""Tests for SQL Lab API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _make_sql_lab_client():
    """Build a TestClient with SQL Lab dependencies mocked."""
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
    app.dependency_overrides[deps.get_db_session] = lambda: mock_session
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    return client, mock_session


class TestGetSchemas:
    @patch("datapulse.api.routes.sql_lab.get_schema_tables")
    def test_get_schemas_success(self, mock_get_tables):
        mock_get_tables.return_value = [
            {
                "table_name": "fct_sales",
                "columns": [{"column_name": "id", "data_type": "integer", "is_nullable": False}],
            }
        ]
        client, _ = _make_sql_lab_client()
        resp = client.get("/api/v1/sql-lab/schemas")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["table_name"] == "fct_sales"


class TestExecuteSQL:
    @patch("datapulse.api.routes.sql_lab.validate_sql")
    def test_execute_success(self, mock_validate):
        mock_validate.return_value = "SELECT 1 AS val"
        client, mock_session = _make_sql_lab_client()

        mock_result = MagicMock()
        mock_result.keys.return_value = ["val"]
        mock_result.__iter__ = lambda self: iter([(1,)])
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/sql-lab/execute",
            json={"sql": "SELECT 1 AS val", "row_limit": 100},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_count"] == 1
        assert data["columns"] == ["val"]
        assert data["sql"] == "SELECT 1 AS val"

    @patch("datapulse.api.routes.sql_lab.validate_sql")
    def test_execute_validation_error(self, mock_validate):
        from datapulse.sql_lab.validator import SQLValidationError

        mock_validate.side_effect = SQLValidationError("DROP not allowed")
        client, _ = _make_sql_lab_client()

        resp = client.post(
            "/api/v1/sql-lab/execute",
            json={"sql": "DROP TABLE x"},
        )
        assert resp.status_code == 422
        assert "DROP not allowed" in resp.json()["detail"]

    @patch("datapulse.api.routes.sql_lab.validate_sql")
    def test_execute_db_error(self, mock_validate):
        mock_validate.return_value = "SELECT 1"
        client, mock_session = _make_sql_lab_client()
        # First call sets search_path, second call fails
        mock_session.execute.side_effect = [None, RuntimeError("connection lost")]

        resp = client.post(
            "/api/v1/sql-lab/execute",
            json={"sql": "SELECT 1"},
        )
        assert resp.status_code == 500
        assert "Query execution failed" in resp.json()["detail"]

    @patch("datapulse.api.routes.sql_lab.validate_sql")
    def test_execute_truncated(self, mock_validate):
        mock_validate.return_value = "SELECT generate_series(1, 20)"
        client, mock_session = _make_sql_lab_client()

        rows = [(i,) for i in range(20)]
        mock_result = MagicMock()
        mock_result.keys.return_value = ["v"]
        mock_result.__iter__ = lambda self: iter(rows)
        # Return None for first execute (SET search_path), mock_result for second
        mock_session.execute.side_effect = [None, mock_result]

        resp = client.post(
            "/api/v1/sql-lab/execute",
            json={"sql": "SELECT generate_series(1,20)", "row_limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["truncated"] is True
        assert data["row_count"] == 5


class TestSerialise:
    def test_serialise_types(self):
        from datetime import date, datetime
        from decimal import Decimal

        from datapulse.api.routes.sql_lab import _serialise

        assert _serialise(None) is None
        assert _serialise(Decimal("10.5")) == 10.5
        assert _serialise(datetime(2025, 1, 1, 12, 0)) == "2025-01-01T12:00:00"
        assert _serialise(date(2025, 1, 1)) == "2025-01-01"
        assert _serialise(42) == 42
        assert _serialise(True) is True
        assert _serialise("s") == "s"
        assert isinstance(_serialise(object()), str)
