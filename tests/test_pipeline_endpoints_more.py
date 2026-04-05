"""Additional tests for pipeline API endpoints — covers SSE stream (lines 126-177),
_sse_event helper (line 190), and n8n webhook failure path (line 271)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from datapulse.pipeline.models import PipelineRunResponse


def _make_response(**overrides):
    defaults = dict(
        id=uuid4(),
        tenant_id=1,
        run_type="full",
        status="pending",
        trigger_source=None,
        started_at=datetime.now(UTC),
        finished_at=None,
        duration_seconds=None,
        rows_loaded=None,
        error_message=None,
        metadata={},
    )
    defaults.update(overrides)
    return PipelineRunResponse(**defaults)


def _make_pipeline_client():
    from datapulse.api import deps
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user, require_pipeline_token
    from datapulse.pipeline.executor import PipelineExecutor
    from datapulse.pipeline.quality_service import QualityService
    from datapulse.pipeline.repository import PipelineRepository
    from datapulse.pipeline.service import PipelineService

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }

    mock_session = MagicMock()
    mock_pl_repo = create_autospec(PipelineRepository, instance=True)
    mock_pl_svc = PipelineService(mock_pl_repo)
    mock_executor = MagicMock(spec=PipelineExecutor)
    mock_quality_svc = MagicMock(spec=QualityService)

    app = create_app()
    app.dependency_overrides[deps.get_db_session] = lambda: mock_session
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[deps.get_pipeline_service] = lambda: mock_pl_svc
    app.dependency_overrides[deps.get_pipeline_executor] = lambda: mock_executor
    app.dependency_overrides[deps.get_quality_service] = lambda: mock_quality_svc
    app.dependency_overrides[get_current_user] = lambda: _dev_user
    app.dependency_overrides[require_pipeline_token] = lambda: None

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    return client, mock_pl_repo, mock_executor, mock_quality_svc


class TestSSEEvent:
    def test_sse_event_format(self):
        from datapulse.api.routes.pipeline import _sse_event

        result = _sse_event("status_change", {"run_id": "abc", "status": "running"})
        assert result.startswith("event: status_change\n")
        assert "data:" in result
        parsed = json.loads(result.split("data: ")[1].strip())
        assert parsed["run_id"] == "abc"
        assert parsed["status"] == "running"


class TestStreamRunProgress:
    def test_stream_run_not_found(self):
        client, mock_repo, _, _ = _make_pipeline_client()
        mock_repo.get_run.return_value = None
        resp = client.get(f"/api/v1/pipeline/runs/{uuid4()}/stream")
        assert resp.status_code == 404

    def test_stream_immediate_terminal(self):
        """When run is already in terminal state, stream returns complete event."""
        client, mock_repo, _, _ = _make_pipeline_client()
        run_id = uuid4()
        run = _make_response(id=run_id, status="success")
        mock_repo.get_run.return_value = run

        resp = client.get(f"/api/v1/pipeline/runs/{run_id}/stream")
        assert resp.status_code == 200
        text = resp.text
        assert "event: status_change" in text
        assert "event: complete" in text

    def test_stream_error_during_poll(self):
        """When polling raises an exception, stream emits error event."""
        client, mock_repo, _, _ = _make_pipeline_client()
        run_id = uuid4()
        run = _make_response(id=run_id, status="running")
        # First call returns run (verify), second call raises
        mock_repo.get_run.side_effect = [run, RuntimeError("DB gone")]

        resp = client.get(f"/api/v1/pipeline/runs/{run_id}/stream")
        assert resp.status_code == 200
        text = resp.text
        assert "event: error" in text

    def test_stream_run_disappears(self):
        """When run becomes None during poll, stream emits error."""
        client, mock_repo, _, _ = _make_pipeline_client()
        run_id = uuid4()
        run = _make_response(id=run_id, status="running")
        mock_repo.get_run.side_effect = [run, None]

        resp = client.get(f"/api/v1/pipeline/runs/{run_id}/stream")
        assert resp.status_code == 200
        assert "event: error" in resp.text


class TestTriggerPipelineOrchestrator:
    @patch("datapulse.scheduler.run_pipeline", new_callable=AsyncMock)
    def test_trigger_returns_202(self, mock_run):
        """Trigger returns 202 and starts pipeline in background."""
        client, mock_repo, _, _ = _make_pipeline_client()
        run = _make_response(status="pending")
        mock_repo.create_run.return_value = run

        resp = client.post(
            "/api/v1/pipeline/trigger",
            json={"source_dir": "/app/data/raw/sales"},
        )
        assert resp.status_code == 202


class TestUpdateRunNotFound:
    def test_update_run_not_found(self):
        client, mock_repo, _, _ = _make_pipeline_client()
        mock_repo.update_run.return_value = None
        resp = client.patch(
            f"/api/v1/pipeline/runs/{uuid4()}",
            json={"status": "running"},
        )
        assert resp.status_code == 404
