"""Tests for POST /api/v1/pipeline/execute/* endpoints."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.deps import get_pipeline_executor
from datapulse.pipeline.models import ExecutionResult


@pytest.fixture
def mock_executor_and_client():
    from datapulse.api import deps
    from datapulse.api.auth import get_current_user, require_pipeline_token
    from datapulse.config import Settings, get_settings

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }
    clean_settings = Settings(_env_file=None, api_key="test-api-key", database_url="")

    app = create_app()
    mock_exec = MagicMock()
    app.dependency_overrides[get_settings] = lambda: clean_settings
    app.dependency_overrides[get_pipeline_executor] = lambda: mock_exec
    app.dependency_overrides[deps.get_tenant_session] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: _dev_user
    app.dependency_overrides[require_pipeline_token] = lambda: None
    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    yield mock_exec, client
    app.dependency_overrides.clear()


class TestExecuteBronze:
    def test_bronze_success(self, mock_executor_and_client):
        mock_exec, client = mock_executor_and_client
        mock_exec.run_bronze.return_value = ExecutionResult(
            success=True,
            rows_loaded=50000,
            duration_seconds=120.5,
        )

        resp = client.post(
            "/api/v1/pipeline/execute/bronze",
            json={"run_id": str(uuid4()), "source_dir": "/app/data/raw/sales"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rows_loaded"] == 50000

    def test_bronze_failure(self, mock_executor_and_client):
        mock_exec, client = mock_executor_and_client
        mock_exec.run_bronze.return_value = ExecutionResult(
            success=False,
            error="No .xlsx files found",
            duration_seconds=0.1,
        )

        resp = client.post(
            "/api/v1/pipeline/execute/bronze",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "No .xlsx" in data["error"]


class TestExecuteDbtStaging:
    def test_staging_success(self, mock_executor_and_client):
        mock_exec, client = mock_executor_and_client
        mock_exec.run_dbt.return_value = ExecutionResult(
            success=True,
            duration_seconds=45.0,
        )

        resp = client.post(
            "/api/v1/pipeline/execute/dbt-staging",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_exec.run_dbt.assert_called_once_with(run_id=ANY, selector="staging")

    def test_staging_failure(self, mock_executor_and_client):
        mock_exec, client = mock_executor_and_client
        mock_exec.run_dbt.return_value = ExecutionResult(
            success=False,
            error="Compilation Error",
            duration_seconds=2.0,
        )

        resp = client.post(
            "/api/v1/pipeline/execute/dbt-staging",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False


class TestExecuteDbtMarts:
    def test_marts_success(self, mock_executor_and_client):
        mock_exec, client = mock_executor_and_client
        mock_exec.run_dbt.return_value = ExecutionResult(
            success=True,
            duration_seconds=90.0,
        )

        resp = client.post(
            "/api/v1/pipeline/execute/dbt-marts",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_exec.run_dbt.assert_called_once_with(run_id=ANY, selector="marts")
