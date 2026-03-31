"""Tests for POST /api/v1/pipeline/trigger endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.deps import get_pipeline_service
from datapulse.pipeline.models import PipelineRunResponse
from datapulse.pipeline.service import PipelineService


def _mock_service():
    run_id = uuid4()
    mock_service = MagicMock(spec=PipelineService)
    mock_service.start_run.return_value = PipelineRunResponse(
        id=run_id,
        tenant_id=1,
        run_type="full",
        status="pending",
        trigger_source="api",
        started_at="2026-03-28T00:00:00Z",
        finished_at=None,
        duration_seconds=None,
        rows_loaded=None,
        error_message=None,
        metadata={},
    )
    return mock_service, run_id


@pytest.fixture
def client():
    app = create_app()
    mock_service, _ = _mock_service()
    app.dependency_overrides[get_pipeline_service] = lambda: mock_service
    yield TestClient(app, headers={"X-API-Key": "test-api-key"})
    app.dependency_overrides.clear()


@pytest.fixture
def mock_service_and_client():
    app = create_app()
    mock_service, run_id = _mock_service()
    app.dependency_overrides[get_pipeline_service] = lambda: mock_service
    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    yield mock_service, run_id, client
    app.dependency_overrides.clear()


class TestTriggerEndpoint:
    @patch("datapulse.api.routes.pipeline.httpx")
    def test_trigger_success(self, mock_httpx, mock_service_and_client):
        mock_service, run_id, client = mock_service_and_client
        mock_httpx.post.return_value = MagicMock(status_code=200)

        resp = client.post("/api/v1/pipeline/trigger", json={})
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending"
        assert "run_id" in data

    @patch("datapulse.api.routes.pipeline.httpx")
    def test_trigger_n8n_unreachable(self, mock_httpx, mock_service_and_client):
        mock_service, run_id, client = mock_service_and_client
        mock_httpx.HTTPError = httpx.HTTPError
        mock_httpx.TimeoutException = httpx.TimeoutException
        mock_httpx.post.side_effect = httpx.ConnectError("Connection refused")

        resp = client.post("/api/v1/pipeline/trigger", json={})
        assert resp.status_code == 202  # run created even if n8n is down

    @patch("datapulse.api.routes.pipeline.httpx")
    def test_trigger_custom_source(self, mock_httpx, mock_service_and_client):
        mock_service, run_id, client = mock_service_and_client
        mock_httpx.post.return_value = MagicMock(status_code=200)

        resp = client.post(
            "/api/v1/pipeline/trigger",
            json={"source_dir": "/app/data/raw/custom", "tenant_id": 2},
        )
        assert resp.status_code == 202

    def test_trigger_path_traversal_rejected(self, mock_service_and_client):
        _, _, client = mock_service_and_client
        resp = client.post(
            "/api/v1/pipeline/trigger",
            json={"source_dir": "/app/data/../../etc/passwd"},
        )
        assert resp.status_code == 422

    def test_trigger_outside_allowed_root_rejected(self, mock_service_and_client):
        _, _, client = mock_service_and_client
        resp = client.post(
            "/api/v1/pipeline/trigger",
            json={"source_dir": "/etc/secrets"},
        )
        assert resp.status_code == 422
