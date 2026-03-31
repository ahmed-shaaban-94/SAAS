"""Tests for PipelineRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4


def _make_row(**overrides):
    """Create a mock DB row with _mapping dict for _row_to_response."""
    defaults = {
        "id": uuid4(),
        "tenant_id": 1,
        "run_type": "full",
        "status": "pending",
        "trigger_source": None,
        "started_at": datetime.now(UTC),
        "finished_at": None,
        "duration_seconds": None,
        "rows_loaded": None,
        "error_message": None,
        "metadata": {},
    }
    defaults.update(overrides)
    row = MagicMock()
    row._mapping = defaults
    return row


class TestCreateRun:
    def test_creates_and_returns(self, pipeline_repo, mock_session):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _make_row(id=run_id)

        from datapulse.pipeline.models import PipelineRunCreate

        data = PipelineRunCreate(run_type="full", trigger_source="manual")
        result = pipeline_repo.create_run(data)

        assert result.id == run_id
        assert result.run_type == "full"
        mock_session.commit.assert_called_once()

    def test_with_metadata(self, pipeline_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = _make_row(
            metadata={"source": "n8n"},
        )
        from datapulse.pipeline.models import PipelineRunCreate

        data = PipelineRunCreate(run_type="bronze", metadata={"source": "n8n"})
        result = pipeline_repo.create_run(data)
        assert result.metadata == {"source": "n8n"}


class TestUpdateRun:
    def test_found(self, pipeline_repo, mock_session):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _make_row(
            id=run_id,
            status="running",
        )
        from datapulse.pipeline.models import PipelineRunUpdate

        data = PipelineRunUpdate(status="running")
        result = pipeline_repo.update_run(run_id, data)
        assert result is not None
        assert result.status == "running"
        mock_session.commit.assert_called_once()

    def test_not_found(self, pipeline_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = None
        from datapulse.pipeline.models import PipelineRunUpdate

        data = PipelineRunUpdate(status="running")
        result = pipeline_repo.update_run(uuid4(), data)
        assert result is None

    def test_empty_update_returns_current(self, pipeline_repo, mock_session):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _make_row(id=run_id)
        from datapulse.pipeline.models import PipelineRunUpdate

        data = PipelineRunUpdate()
        result = pipeline_repo.update_run(run_id, data)
        assert result is not None
        assert result.id == run_id


class TestGetRun:
    def test_found(self, pipeline_repo, mock_session):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _make_row(id=run_id)
        result = pipeline_repo.get_run(run_id)
        assert result is not None
        assert result.id == run_id

    def test_not_found(self, pipeline_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = None
        result = pipeline_repo.get_run(uuid4())
        assert result is None


class TestListRuns:
    def test_empty(self, pipeline_repo, mock_session):
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        rows_result = MagicMock()
        rows_result.fetchall.return_value = []
        mock_session.execute.side_effect = [count_result, rows_result]

        result = pipeline_repo.list_runs()
        assert result.total == 0
        assert result.items == []
        assert result.offset == 0
        assert result.limit == 20

    def test_with_status_filter(self, pipeline_repo, mock_session):
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        rows_result = MagicMock()
        rows_result.fetchall.return_value = [_make_row(status="running")]
        mock_session.execute.side_effect = [count_result, rows_result]

        result = pipeline_repo.list_runs(status="running")
        assert result.total == 1
        assert len(result.items) == 1

    def test_with_pagination(self, pipeline_repo, mock_session):
        count_result = MagicMock()
        count_result.scalar_one.return_value = 50
        rows_result = MagicMock()
        rows_result.fetchall.return_value = [_make_row()]
        mock_session.execute.side_effect = [count_result, rows_result]

        result = pipeline_repo.list_runs(offset=10, limit=5)
        assert result.total == 50
        assert result.offset == 10
        assert result.limit == 5


class TestGetLatestRun:
    def test_found(self, pipeline_repo, mock_session):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _make_row(id=run_id)
        result = pipeline_repo.get_latest_run()
        assert result is not None
        assert result.id == run_id

    def test_not_found(self, pipeline_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = None
        result = pipeline_repo.get_latest_run()
        assert result is None

    def test_with_type_filter(self, pipeline_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = _make_row(
            run_type="bronze",
        )
        result = pipeline_repo.get_latest_run(run_type="bronze")
        assert result is not None
        assert result.run_type == "bronze"
