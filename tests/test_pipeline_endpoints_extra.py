"""Extra pipeline endpoint tests — trigger, execute, quality, cache."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from datapulse.pipeline.models import (
    ExecutionResult,
    PipelineRunResponse,
)
from datapulse.pipeline.quality import QualityCheckList, QualityReport


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
    """Build a TestClient with all pipeline dependencies mocked."""
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


class TestTriggerPipeline:
    @patch("datapulse.scheduler.run_pipeline", new_callable=AsyncMock)
    def test_trigger_success(self, mock_run):
        client, mock_repo, _, _ = _make_pipeline_client()
        run = _make_response(status="pending")
        mock_repo.create_run.return_value = run
        resp = client.post("/api/v1/pipeline/trigger", json={"source_dir": "/app/data/raw/sales"})
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending"

    @patch("datapulse.scheduler.run_pipeline", new_callable=AsyncMock)
    def test_trigger_default_body(self, mock_run):
        client, mock_repo, _, _ = _make_pipeline_client()
        run = _make_response(status="pending")
        mock_repo.create_run.return_value = run
        resp = client.post("/api/v1/pipeline/trigger")
        assert resp.status_code == 202


class TestExecuteEndpoints:
    def test_execute_bronze(self):
        client, _, mock_executor, _ = _make_pipeline_client()
        mock_executor.run_bronze.return_value = ExecutionResult(
            success=True, rows_loaded=50000, duration_seconds=5.0
        )
        resp = client.post(
            "/api/v1/pipeline/execute/bronze",
            json={"run_id": str(uuid4()), "source_dir": "/app/data/raw/sales"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_execute_dbt_staging(self):
        client, _, mock_executor, _ = _make_pipeline_client()
        mock_executor.run_dbt.return_value = ExecutionResult(success=True, duration_seconds=10.0)
        resp = client.post(
            "/api/v1/pipeline/execute/dbt-staging",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200

    def test_execute_dbt_marts(self):
        client, _, mock_executor, _ = _make_pipeline_client()
        mock_executor.run_dbt.return_value = ExecutionResult(success=True, duration_seconds=8.0)
        resp = client.post(
            "/api/v1/pipeline/execute/dbt-marts",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200

    def test_execute_forecasting(self):
        client, _, mock_executor, _ = _make_pipeline_client()
        mock_executor.run_forecasting.return_value = ExecutionResult(
            success=True, rows_loaded=100, duration_seconds=3.0
        )
        resp = client.post(
            "/api/v1/pipeline/execute/forecasting",
            json={"run_id": str(uuid4())},
        )
        assert resp.status_code == 200


class TestQualityEndpoints:
    def test_get_quality_checks(self):
        client, mock_repo, _, mock_quality_svc = _make_pipeline_client()
        run_id = uuid4()
        mock_repo.get_run.return_value = _make_response(id=run_id)
        mock_quality_svc.get_checks.return_value = QualityCheckList(items=[], total=0)
        resp = client.get(f"/api/v1/pipeline/runs/{run_id}/quality")
        assert resp.status_code == 200

    def test_get_quality_checks_run_not_found(self):
        client, mock_repo, _, _ = _make_pipeline_client()
        mock_repo.get_run.return_value = None
        resp = client.get(f"/api/v1/pipeline/runs/{uuid4()}/quality")
        assert resp.status_code == 404

    def test_get_quality_checks_invalid_stage(self):
        client, mock_repo, _, _ = _make_pipeline_client()
        run_id = uuid4()
        mock_repo.get_run.return_value = _make_response(id=run_id)
        resp = client.get(f"/api/v1/pipeline/runs/{run_id}/quality?stage=bogus")
        assert resp.status_code == 422

    def test_execute_quality_check(self):
        client, _, _, mock_quality_svc = _make_pipeline_client()
        run_id = uuid4()
        mock_quality_svc.run_checks_for_stage.return_value = QualityReport(
            pipeline_run_id=run_id,
            stage="bronze",
            checks=[],
            all_passed=True,
            gate_passed=True,
            checked_at=datetime.now(UTC),
        )
        resp = client.post(
            "/api/v1/pipeline/execute/quality-check",
            json={"run_id": str(run_id), "stage": "bronze"},
        )
        assert resp.status_code == 200
        assert resp.json()["gate_passed"] is True


class TestUpdateRunCacheInvalidation:
    @patch("datapulse.api.routes.pipeline.cache_invalidate_pattern", return_value=5)
    def test_update_to_success_invalidates_cache(self, mock_cache):
        client, mock_repo, _, _ = _make_pipeline_client()
        run_id = uuid4()
        mock_repo.update_run.return_value = _make_response(id=run_id, status="success")
        resp = client.patch(
            f"/api/v1/pipeline/runs/{run_id}",
            json={"status": "success"},
        )
        assert resp.status_code == 200
        mock_cache.assert_called_once_with("datapulse:analytics:*")
