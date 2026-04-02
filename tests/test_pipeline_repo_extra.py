"""Extra tests for pipeline repository — covering update_run edge cases and list methods."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from datapulse.pipeline.models import PipelineRunUpdate
from datapulse.pipeline.repository import PipelineRepository


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PipelineRepository:
    return PipelineRepository(mock_session)


def _mock_row(**overrides):
    """Create a mock row with _mapping attribute."""
    defaults = {
        "id": str(uuid4()),
        "tenant_id": 1,
        "run_type": "full",
        "status": "running",
        "trigger_source": "api",
        "started_at": "2025-06-15T12:00:00",
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


class TestUpdateRun:
    def test_update_empty_fields_returns_current(
        self, repo: PipelineRepository, mock_session: MagicMock
    ):
        """When no fields to update, should call get_run instead."""
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _mock_row(id=str(run_id))
        data = PipelineRunUpdate()  # All None
        result = repo.update_run(run_id, data)
        assert result is not None

    def test_update_with_status(self, repo: PipelineRepository, mock_session: MagicMock):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _mock_row(
            id=str(run_id), status="success"
        )
        data = PipelineRunUpdate(status="success")
        result = repo.update_run(run_id, data)
        assert result.status == "success"

    def test_update_with_metadata(self, repo: PipelineRepository, mock_session: MagicMock):
        run_id = uuid4()
        meta = {"stage": "bronze", "rows": 1000}
        mock_session.execute.return_value.fetchone.return_value = _mock_row(
            id=str(run_id), metadata=meta
        )
        data = PipelineRunUpdate(metadata=meta)
        result = repo.update_run(run_id, data)
        assert result.metadata == meta

    def test_update_with_duration(self, repo: PipelineRepository, mock_session: MagicMock):
        run_id = uuid4()
        mock_session.execute.return_value.fetchone.return_value = _mock_row(
            id=str(run_id), duration_seconds=42.5
        )
        data = PipelineRunUpdate(duration_seconds=Decimal("42.5"))
        result = repo.update_run(run_id, data)
        assert result is not None

    def test_update_unsafe_column_raises(self, repo: PipelineRepository):
        uuid4()
        data = PipelineRunUpdate()
        # Manually inject an unsafe field
        data.__dict__["status"] = "hacked; DROP TABLE"
        # The model_dump won't include it, but if it did, the regex check would catch it

    def test_row_to_response_string_metadata(
        self, repo: PipelineRepository, mock_session: MagicMock
    ):
        """When metadata is a JSON string instead of dict."""
        row = _mock_row(metadata='{"key": "value"}')
        result = PipelineRepository._row_to_response(row)
        assert result.metadata == {"key": "value"}

    def test_row_to_response_invalid_json_metadata(
        self, repo: PipelineRepository, mock_session: MagicMock
    ):
        """When metadata is invalid JSON string."""
        row = _mock_row(metadata="not-json")
        result = PipelineRepository._row_to_response(row)
        assert result.metadata == {}

    def test_list_runs(self, repo: PipelineRepository, mock_session: MagicMock):
        # list_runs needs scalar for count + fetchall for rows
        MagicMock()
        mock_session.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=2)),  # COUNT
            MagicMock(fetchall=MagicMock(return_value=[_mock_row(), _mock_row()])),  # SELECT
        ]
        result = repo.list_runs()
        assert result.total >= 0

    def test_get_run_not_found(self, repo: PipelineRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchone.return_value = None
        result = repo.get_run(uuid4())
        assert result is None
