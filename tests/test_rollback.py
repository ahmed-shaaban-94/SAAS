"""Tests for pipeline rollback utilities."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from datapulse.pipeline.rollback import (
    rollback_bronze,
    rollback_forecasting,
    rollback_stage,
)


class TestRollbackBronze:
    def test_deletes_rows_and_commits(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 500
        run_id = uuid4()

        deleted = rollback_bronze(session, run_id)

        assert deleted == 500
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    def test_returns_zero_on_exception(self):
        session = MagicMock()
        session.execute.side_effect = Exception("DB error")
        run_id = uuid4()

        deleted = rollback_bronze(session, run_id)

        assert deleted == 0
        session.rollback.assert_called_once()

    def test_passes_run_id_as_parameter(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 0
        run_id = uuid4()

        rollback_bronze(session, run_id)

        call_args = session.execute.call_args
        assert call_args[0][1]["run_id"] == str(run_id)


class TestRollbackForecasting:
    def test_deletes_rows_and_commits(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 100
        run_id = uuid4()

        deleted = rollback_forecasting(session, run_id)

        assert deleted == 100
        session.commit.assert_called_once()

    def test_returns_zero_on_exception(self):
        session = MagicMock()
        session.execute.side_effect = Exception("table not found")
        run_id = uuid4()

        deleted = rollback_forecasting(session, run_id)

        assert deleted == 0
        session.rollback.assert_called_once()


class TestRollbackStage:
    def test_dispatches_bronze(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 10
        run_id = uuid4()

        deleted = rollback_stage(session, "bronze", run_id)

        assert deleted == 10

    def test_dispatches_forecasting(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 5
        run_id = uuid4()

        deleted = rollback_stage(session, "forecasting", run_id)

        assert deleted == 5

    def test_returns_zero_for_idempotent_stage(self):
        session = MagicMock()
        run_id = uuid4()

        for stage in ["silver", "gold", "quality_bronze", "unknown"]:
            deleted = rollback_stage(session, stage, run_id)
            assert deleted == 0
            session.execute.assert_not_called()
