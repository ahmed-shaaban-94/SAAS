"""Tests for SampleLoadService — Phase 2 Task 2 / #401.

Orchestrates:
1. Clearing prior sample rows + inserting a fresh batch (via sample_data)
2. Creating a pipeline_run marker (so Pipeline Health shows the run)
3. Seeding synthetic passing quality_checks (so the Run Detail looks healthy)

Uses mocked PipelineService + QualityRepository — no DB, no pipeline executor.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from datapulse.onboarding.models import SampleLoadResult
from datapulse.onboarding.sample_service import SampleLoadService


@pytest.fixture()
def mock_session():
    session = MagicMock()
    # sample_data.clear_sample_rows reads rowcount; insert_sample_rows does not.
    clear_result = MagicMock()
    clear_result.rowcount = 0
    session.execute.return_value = clear_result
    return session


@pytest.fixture()
def mock_pipeline_service():
    svc = MagicMock()
    run_id = uuid4()
    created = MagicMock()
    created.id = run_id
    svc.start_run.return_value = created
    completed = MagicMock()
    completed.id = run_id
    svc.complete_run.return_value = completed
    svc.run_id = run_id  # expose for assertions
    return svc


@pytest.fixture()
def mock_quality_repo():
    repo = MagicMock()
    repo.save_checks.return_value = []
    return repo


@pytest.fixture()
def service(mock_session, mock_pipeline_service, mock_quality_repo):
    return SampleLoadService(
        session=mock_session,
        pipeline_service=mock_pipeline_service,
        quality_repo=mock_quality_repo,
    )


@pytest.mark.unit
class TestSampleLoadService:
    def test_returns_sample_load_result_with_run_id(self, service, mock_pipeline_service):
        result = service.load(tenant_id=1, user_id="u-1", row_count=20)

        assert isinstance(result, SampleLoadResult)
        assert result.rows_loaded == 20
        assert result.pipeline_run_id == str(mock_pipeline_service.run_id)
        assert result.duration_seconds >= 0

    def test_creates_pipeline_run_with_sample_trigger(self, service, mock_pipeline_service):
        service.load(tenant_id=1, user_id="u-1", row_count=20)

        assert mock_pipeline_service.start_run.call_count == 1
        data_arg = mock_pipeline_service.start_run.call_args.args[0]
        assert data_arg.run_type == "full"
        assert data_arg.trigger_source == "onboarding_sample"
        # Metadata should mark this as a sample load for later filtering.
        assert data_arg.metadata.get("source") == "sample"

    def test_marks_run_completed_as_success(self, service, mock_pipeline_service):
        service.load(tenant_id=1, user_id="u-1", row_count=20)

        assert mock_pipeline_service.complete_run.call_count == 1
        kwargs = mock_pipeline_service.complete_run.call_args.kwargs
        assert kwargs["rows_loaded"] == 20

    def test_seeds_passing_quality_checks_across_all_stages(
        self, service, mock_pipeline_service, mock_quality_repo
    ):
        service.load(tenant_id=1, user_id="u-1", row_count=20)

        assert mock_quality_repo.save_checks.call_count == 1
        args = mock_quality_repo.save_checks.call_args
        run_id = args.args[0]
        checks = args.args[1]
        assert run_id == mock_pipeline_service.run_id
        # At least one check per stage, all passing.
        stages = {c.stage for c in checks}
        assert {"bronze", "silver", "gold"}.issubset(stages)
        assert all(c.passed for c in checks)

    def test_quality_checks_scoped_to_caller_tenant(self, service, mock_quality_repo):
        service.load(tenant_id=9, user_id="u-9", row_count=10)
        kwargs = mock_quality_repo.save_checks.call_args.kwargs
        assert kwargs.get("tenant_id") == 9

    def test_rolls_back_run_on_insertion_failure(self, service, mock_pipeline_service):
        """If sample insertion raises, the pipeline run is marked failed, not success."""
        with (
            patch(
                "datapulse.onboarding.sample_service.load_sample",
                side_effect=RuntimeError("simulated db down"),
            ),
            pytest.raises(RuntimeError, match="simulated db down"),
        ):
            service.load(tenant_id=1, user_id="u-1", row_count=20)

        mock_pipeline_service.complete_run.assert_not_called()
        mock_pipeline_service.fail_run.assert_called_once()
        err = mock_pipeline_service.fail_run.call_args.args[1]
        assert "sample" in err.lower()
