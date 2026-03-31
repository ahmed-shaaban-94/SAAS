"""Tests for QualityRepository — data-access layer for quality_checks table."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from datapulse.pipeline.quality import (
    QualityCheckList,
    QualityCheckResponse,
    QualityCheckResult,
)
from datapulse.pipeline.quality_repository import QualityRepository


def _make_row(**overrides):
    """Build a mock DB row with _mapping."""
    defaults = {
        "id": 1,
        "tenant_id": 1,
        "pipeline_run_id": uuid4(),
        "check_name": "row_count",
        "stage": "bronze",
        "severity": "error",
        "passed": True,
        "message": "50000 rows",
        "details": {"row_count": 50000},
        "checked_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    row = MagicMock()
    row._mapping = defaults
    return row


@pytest.fixture()
def session():
    return MagicMock()


@pytest.fixture()
def repo(session):
    return QualityRepository(session)


class TestRowToResponse:
    def test_converts_dict_details(self):
        row = _make_row(details={"key": "val"})
        resp = QualityRepository._row_to_response(row)
        assert isinstance(resp, QualityCheckResponse)
        assert resp.details == {"key": "val"}

    def test_converts_json_string_details(self):
        row = _make_row(details='{"key": "val"}')
        resp = QualityRepository._row_to_response(row)
        assert resp.details == {"key": "val"}

    def test_invalid_json_string_returns_empty_dict(self):
        row = _make_row(details="not valid json")
        resp = QualityRepository._row_to_response(row)
        assert resp.details == {}

    def test_none_details_returns_empty_dict(self):
        row = _make_row(details=None)
        resp = QualityRepository._row_to_response(row)
        assert resp.details == {}


class TestSaveChecks:
    def test_inserts_and_commits(self, repo, session):
        run_id = uuid4()
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={"row_count": 50000},
            ),
        ]
        session.execute.return_value.fetchone.return_value = _make_row(pipeline_run_id=run_id)

        results = repo.save_checks(run_id, checks, tenant_id=1)

        assert len(results) == 1
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_multiple_checks(self, repo, session):
        run_id = uuid4()
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={},
            ),
            QualityCheckResult(
                check_name="null_rate",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={},
            ),
        ]
        session.execute.return_value.fetchone.return_value = _make_row(pipeline_run_id=run_id)

        results = repo.save_checks(run_id, checks, tenant_id=1)

        assert len(results) == 2
        assert session.execute.call_count == 2

    def test_rollback_on_error(self, repo, session):
        run_id = uuid4()
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={},
            ),
        ]
        session.execute.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            repo.save_checks(run_id, checks)

        session.rollback.assert_called_once()


class TestGetChecksForRun:
    def test_returns_check_list(self, repo, session):
        run_id = uuid4()
        row = _make_row(pipeline_run_id=run_id)
        session.execute.return_value.scalar_one.return_value = 1
        session.execute.return_value.fetchall.return_value = [row]

        result = repo.get_checks_for_run(run_id, stage="bronze")

        assert isinstance(result, QualityCheckList)
        assert result.total == 1
        assert len(result.items) == 1

    def test_empty_results(self, repo, session):
        run_id = uuid4()
        # First call for count, second for select
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        select_result = MagicMock()
        select_result.fetchall.return_value = []
        session.execute.side_effect = [count_result, select_result]

        result = repo.get_checks_for_run(run_id)

        assert result.total == 0
        assert result.items == []

    def test_no_stage_filter(self, repo, session):
        run_id = uuid4()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        select_result = MagicMock()
        select_result.fetchall.return_value = []
        session.execute.side_effect = [count_result, select_result]

        repo.get_checks_for_run(run_id, stage=None)

        # Both calls should pass stage=None
        for call in session.execute.call_args_list:
            params = call[0][1]
            assert params["stage"] is None
