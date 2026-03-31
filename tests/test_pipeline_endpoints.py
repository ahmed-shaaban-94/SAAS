"""Tests for pipeline API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from datapulse.pipeline.models import PipelineRunList, PipelineRunResponse


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


class TestListRuns:
    def test_empty(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.list_runs.return_value = PipelineRunList(
            items=[],
            total=0,
            offset=0,
            limit=20,
        )
        resp = client.get("/api/v1/pipeline/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_with_status_filter(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.list_runs.return_value = PipelineRunList(
            items=[],
            total=0,
            offset=0,
            limit=20,
        )
        resp = client.get("/api/v1/pipeline/runs?status=running")
        assert resp.status_code == 200

    def test_invalid_status(self, pipeline_api_client):
        client, _ = pipeline_api_client
        resp = client.get("/api/v1/pipeline/runs?status=bogus")
        assert resp.status_code == 422

    def test_pagination_params(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.list_runs.return_value = PipelineRunList(
            items=[],
            total=50,
            offset=10,
            limit=5,
        )
        resp = client.get("/api/v1/pipeline/runs?offset=10&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 10
        assert data["limit"] == 5


class TestGetLatestRun:
    def test_found(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.get_latest_run.return_value = _make_response()
        resp = client.get("/api/v1/pipeline/runs/latest")
        assert resp.status_code == 200

    def test_not_found(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.get_latest_run.return_value = None
        resp = client.get("/api/v1/pipeline/runs/latest")
        assert resp.status_code == 404

    def test_with_type_filter(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.get_latest_run.return_value = _make_response(run_type="incremental")
        resp = client.get("/api/v1/pipeline/runs/latest?run_type=incremental")
        assert resp.status_code == 200


class TestGetRun:
    def test_found(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        run_id = uuid4()
        mock_repo.get_run.return_value = _make_response(id=run_id)
        resp = client.get(f"/api/v1/pipeline/runs/{run_id}")
        assert resp.status_code == 200

    def test_not_found(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.get_run.return_value = None
        resp = client.get(f"/api/v1/pipeline/runs/{uuid4()}")
        assert resp.status_code == 404


class TestCreateRun:
    def test_success(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.create_run.return_value = _make_response()
        resp = client.post(
            "/api/v1/pipeline/runs",
            json={"run_type": "full", "trigger_source": "manual"},
        )
        assert resp.status_code == 201

    def test_minimal_body(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.create_run.return_value = _make_response()
        resp = client.post(
            "/api/v1/pipeline/runs",
            json={"run_type": "full"},
        )
        assert resp.status_code == 201

    def test_missing_run_type(self, pipeline_api_client):
        client, _ = pipeline_api_client
        resp = client.post("/api/v1/pipeline/runs", json={})
        assert resp.status_code == 422


class TestUpdateRun:
    def test_success(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        run_id = uuid4()
        mock_repo.update_run.return_value = _make_response(id=run_id, status="running")
        resp = client.patch(
            f"/api/v1/pipeline/runs/{run_id}",
            json={"status": "running"},
        )
        assert resp.status_code == 200

    def test_not_found(self, pipeline_api_client):
        client, mock_repo = pipeline_api_client
        mock_repo.update_run.return_value = None
        resp = client.patch(
            f"/api/v1/pipeline/runs/{uuid4()}",
            json={"status": "running"},
        )
        assert resp.status_code == 404

    def test_invalid_status(self, pipeline_api_client):
        client, _ = pipeline_api_client
        resp = client.patch(
            f"/api/v1/pipeline/runs/{uuid4()}",
            json={"status": "bogus"},
        )
        assert resp.status_code == 422
