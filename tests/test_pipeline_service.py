"""Tests for PipelineService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from datapulse.pipeline.models import (
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
)


def _make_response(**overrides):
    defaults = dict(
        id=uuid4(),
        tenant_id=1,
        run_type="full_refresh",
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


class TestStartRun:
    def test_delegates(self, pipeline_service, mock_pipeline_repo):
        expected = _make_response()
        mock_pipeline_repo.create_run.return_value = expected
        data = PipelineRunCreate(run_type="full_refresh")
        result = pipeline_service.start_run(data)
        assert result == expected
        mock_pipeline_repo.create_run.assert_called_once_with(data, 1)


class TestUpdateStatus:
    def test_valid_status(self, pipeline_service, mock_pipeline_repo):
        expected = _make_response(status="running")
        mock_pipeline_repo.update_run.return_value = expected
        run_id = uuid4()
        data = PipelineRunUpdate(status="running")
        result = pipeline_service.update_status(run_id, data)
        assert result == expected

    def test_invalid_status(self, pipeline_service):
        data = PipelineRunUpdate(status="bogus")
        with pytest.raises(ValueError, match="Invalid status"):
            pipeline_service.update_status(uuid4(), data)

    def test_none_status_skips_validation(self, pipeline_service, mock_pipeline_repo):
        expected = _make_response()
        mock_pipeline_repo.update_run.return_value = expected
        data = PipelineRunUpdate(rows_loaded=500)
        result = pipeline_service.update_status(uuid4(), data)
        assert result == expected


class TestCompleteRun:
    def test_completes(self, pipeline_service, mock_pipeline_repo):
        run_id = uuid4()
        existing = _make_response(
            id=run_id,
            started_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        mock_pipeline_repo.get_run.return_value = existing
        completed = _make_response(id=run_id, status="success")
        mock_pipeline_repo.update_run.return_value = completed

        result = pipeline_service.complete_run(run_id, rows_loaded=1000)
        assert result is not None
        assert result.status == "success"
        mock_pipeline_repo.update_run.assert_called_once()

    def test_not_found(self, pipeline_service, mock_pipeline_repo):
        mock_pipeline_repo.get_run.return_value = None
        result = pipeline_service.complete_run(uuid4())
        assert result is None


class TestFailRun:
    def test_fails(self, pipeline_service, mock_pipeline_repo):
        run_id = uuid4()
        existing = _make_response(
            id=run_id,
            started_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        mock_pipeline_repo.get_run.return_value = existing
        failed = _make_response(id=run_id, status="failed")
        mock_pipeline_repo.update_run.return_value = failed

        result = pipeline_service.fail_run(run_id, "DB connection lost")
        assert result is not None
        assert result.status == "failed"

    def test_not_found(self, pipeline_service, mock_pipeline_repo):
        mock_pipeline_repo.get_run.return_value = None
        result = pipeline_service.fail_run(uuid4(), "error")
        assert result is None


class TestGetRun:
    def test_delegates(self, pipeline_service, mock_pipeline_repo):
        expected = _make_response()
        mock_pipeline_repo.get_run.return_value = expected
        result = pipeline_service.get_run(expected.id)
        assert result == expected


class TestListRuns:
    def test_delegates(self, pipeline_service, mock_pipeline_repo):
        expected = PipelineRunList(items=[], total=0, offset=0, limit=20)
        mock_pipeline_repo.list_runs.return_value = expected
        result = pipeline_service.list_runs()
        assert result == expected

    def test_invalid_status_filter(self, pipeline_service):
        with pytest.raises(ValueError, match="Invalid status"):
            pipeline_service.list_runs(status="bogus")


class TestGetLatestRun:
    def test_delegates(self, pipeline_service, mock_pipeline_repo):
        expected = _make_response()
        mock_pipeline_repo.get_latest_run.return_value = expected
        result = pipeline_service.get_latest_run()
        assert result == expected
