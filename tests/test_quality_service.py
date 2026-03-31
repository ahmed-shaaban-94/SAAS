"""Tests for QualityService — quality gate orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec, patch
from uuid import uuid4

import pytest

from datapulse.config import Settings
from datapulse.pipeline.quality import (
    QualityCheckList,
    QualityCheckResult,
    QualityReport,
)
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.quality_service import QualityService


@pytest.fixture()
def mock_repo():
    return create_autospec(QualityRepository, instance=True)


@pytest.fixture()
def mock_session():
    return MagicMock()


@pytest.fixture()
def settings():
    return Settings(_env_file=None, api_key="test", database_url="")


@pytest.fixture()
def service(mock_repo, mock_session, settings):
    return QualityService(mock_repo, mock_session, settings)


class TestRunChecksForStage:
    def test_invalid_stage_raises(self, service):
        with pytest.raises(ValueError, match="Invalid stage"):
            service.run_checks_for_stage(uuid4(), "invalid")

    def test_bronze_runs_checks_and_persists(self, service, mock_repo, mock_session):
        run_id = uuid4()
        mock_repo.save_checks.return_value = []

        with patch("datapulse.pipeline.quality_service.STAGE_CHECKS") as mock_stages:
            check_fn = MagicMock()
            check_fn.__name__ = "check_row_count"
            check_fn.return_value = QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={"row_count": 50000},
            )
            mock_stages.get.return_value = [check_fn]

            report = service.run_checks_for_stage(run_id, "bronze")

        assert isinstance(report, QualityReport)
        assert report.stage == "bronze"
        assert report.all_passed is True
        assert report.gate_passed is True
        assert len(report.checks) == 1
        mock_repo.save_checks.assert_called_once()

    def test_check_exception_produces_failed_result(self, service, mock_repo):
        run_id = uuid4()
        mock_repo.save_checks.return_value = []

        with patch("datapulse.pipeline.quality_service.STAGE_CHECKS") as mock_stages:
            check_fn = MagicMock()
            check_fn.__name__ = "check_row_count"
            check_fn.side_effect = RuntimeError("DB connection failed")
            mock_stages.get.return_value = [check_fn]

            report = service.run_checks_for_stage(run_id, "bronze")

        assert report.gate_passed is False
        assert report.checks[0].passed is False
        assert "unexpected exception" in report.checks[0].message

    def test_null_rate_receives_stage_kwarg(self, service, mock_repo, mock_session):
        """check_null_rate is dispatched with stage=... kwarg."""
        run_id = uuid4()
        mock_repo.save_checks.return_value = []

        with (
            patch("datapulse.pipeline.quality_service.STAGE_CHECKS") as mock_stages,
            patch("datapulse.pipeline.quality_service.check_null_rate") as mock_null,
        ):
            mock_null.return_value = QualityCheckResult(
                check_name="null_rate",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={},
            )
            # Make check_null_rate identity match
            mock_stages.get.return_value = [mock_null]

            service.run_checks_for_stage(run_id, "bronze")

        mock_null.assert_called_once_with(mock_session, run_id, stage="bronze")

    def test_dbt_tests_receives_selector_and_settings(self, service, mock_repo, settings):
        """run_dbt_tests is dispatched with selector and settings."""
        run_id = uuid4()
        mock_repo.save_checks.return_value = []

        with (
            patch("datapulse.pipeline.quality_service.STAGE_CHECKS") as mock_stages,
            patch("datapulse.pipeline.quality_service.run_dbt_tests") as mock_dbt,
        ):
            mock_dbt.return_value = QualityCheckResult(
                check_name="dbt_tests",
                stage="gold",
                severity="error",
                passed=True,
                message=None,
                details={},
            )
            mock_stages.get.return_value = [mock_dbt]

            service.run_checks_for_stage(run_id, "gold")

        mock_dbt.assert_called_once_with(run_id, "marts", settings)

    def test_gate_passed_false_when_error_check_fails(self, service, mock_repo):
        run_id = uuid4()
        mock_repo.save_checks.return_value = []

        with patch("datapulse.pipeline.quality_service.STAGE_CHECKS") as mock_stages:
            check_fn = MagicMock()
            check_fn.__name__ = "check_row_count"
            check_fn.return_value = QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=False,
                message="No rows",
                details={},
            )
            mock_stages.get.return_value = [check_fn]

            report = service.run_checks_for_stage(run_id, "bronze")

        assert report.gate_passed is False
        assert report.all_passed is False

    def test_warn_severity_does_not_block_gate(self, service, mock_repo):
        run_id = uuid4()
        mock_repo.save_checks.return_value = []

        with patch("datapulse.pipeline.quality_service.STAGE_CHECKS") as mock_stages:
            check_fn = MagicMock()
            check_fn.__name__ = "check_row_delta"
            check_fn.return_value = QualityCheckResult(
                check_name="row_delta",
                stage="bronze",
                severity="warn",
                passed=False,
                message="Big delta",
                details={},
            )
            mock_stages.get.return_value = [check_fn]

            report = service.run_checks_for_stage(run_id, "bronze")

        assert report.gate_passed is True  # warn doesn't block
        assert report.all_passed is False


class TestGetChecks:
    def test_delegates_to_repo(self, service, mock_repo):
        run_id = uuid4()
        expected = QualityCheckList(items=[], total=0)
        mock_repo.get_checks_for_run.return_value = expected

        result = service.get_checks(run_id, stage="bronze")

        assert result is expected
        mock_repo.get_checks_for_run.assert_called_once_with(run_id, stage="bronze")

    def test_no_stage_filter(self, service, mock_repo):
        run_id = uuid4()
        expected = QualityCheckList(items=[], total=0)
        mock_repo.get_checks_for_run.return_value = expected

        service.get_checks(run_id)

        mock_repo.get_checks_for_run.assert_called_once_with(run_id, stage=None)
