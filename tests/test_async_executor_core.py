"""Tests for datapulse.tasks.async_executor — Redis-backed query execution."""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from datapulse.tasks.async_executor import (
    QueryCapacityExceededError,
    _query_timeout,
    _serialise,
    get_job_result,
)

# ---------------------------------------------------------------------------
# _serialise
# ---------------------------------------------------------------------------


class TestSerialise:
    def test_none(self):
        assert _serialise(None) is None

    def test_decimal(self):
        assert _serialise(Decimal("12.34")) == 12.34

    def test_datetime(self):
        dt = datetime(2025, 3, 1, 12, 0, 0)
        assert _serialise(dt) == "2025-03-01T12:00:00"

    def test_date(self):
        d = date(2025, 3, 1)
        assert _serialise(d) == "2025-03-01"

    def test_int(self):
        assert _serialise(42) == 42

    def test_float(self):
        assert _serialise(3.14) == 3.14

    def test_bool(self):
        assert _serialise(True) is True

    def test_str(self):
        assert _serialise("hello") == "hello"

    def test_unknown_type(self):
        assert _serialise(b"bytes") == "b'bytes'"


# ---------------------------------------------------------------------------
# _get_job_client
# ---------------------------------------------------------------------------


def test_get_job_client_returns_none_when_redis_empty():
    """Returns None when redis_url is empty."""
    with patch("datapulse.tasks.async_executor.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(redis_url="")

        from datapulse.tasks.async_executor import _get_job_client

        assert _get_job_client() is None


def test_get_job_client_returns_none_on_exception():
    """Returns None when Redis connection fails."""
    import redis as _real_redis

    with (
        patch("datapulse.tasks.async_executor.get_settings") as mock_settings,
        patch("datapulse.tasks.async_executor.redis") as mock_redis,
    ):
        mock_settings.return_value = MagicMock(redis_url="redis://localhost:6379/0")
        # Preserve real exception classes so `except` clauses work
        mock_redis.ConnectionError = _real_redis.ConnectionError
        mock_redis.RedisError = _real_redis.RedisError
        mock_redis.from_url.side_effect = _real_redis.ConnectionError("refused")

        from datapulse.tasks.async_executor import _get_job_client

        assert _get_job_client() is None


# ---------------------------------------------------------------------------
# get_job_result
# ---------------------------------------------------------------------------


def test_get_job_result_returns_none_when_no_client():
    """Returns None when Redis client is unavailable."""
    with patch("datapulse.tasks.async_executor._get_job_client", return_value=None):
        assert get_job_result("job-123") is None


def test_get_job_result_returns_none_for_missing_key():
    """Returns None when job ID doesn't exist in Redis."""
    mock_client = MagicMock()
    mock_client.get.return_value = None

    with patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client):
        assert get_job_result("nonexistent") is None


def test_get_job_result_returns_complete_job():
    """Returns parsed job data for a completed job."""
    job_data = {"status": "complete", "columns": ["a"], "rows": [[1]], "row_count": 1}
    mock_client = MagicMock()
    mock_client.get.return_value = json.dumps(job_data)

    with patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client):
        result = get_job_result("job-ok")
        assert result["status"] == "complete"
        assert result["row_count"] == 1


def test_get_job_result_detects_stale_running_job():
    """Marks a running job as failed if it exceeds the stale threshold."""
    stale_time = time.time() - (_query_timeout() + 120)
    job_data = {"status": "running", "submitted_at": stale_time}
    mock_client = MagicMock()
    mock_client.get.return_value = json.dumps(job_data)

    with patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client):
        result = get_job_result("stale-job")
        assert result["status"] == "failed"
        assert "stale" in result["error"].lower()


def test_get_job_result_does_not_flag_recent_running_job():
    """A recently submitted running job is not marked stale."""
    recent_time = time.time() - 10  # 10 seconds ago
    job_data = {"status": "running", "submitted_at": recent_time}
    mock_client = MagicMock()
    mock_client.get.return_value = json.dumps(job_data)

    with patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client):
        result = get_job_result("fresh-job")
        assert result["status"] == "running"


# ---------------------------------------------------------------------------
# _run_query_sync
# ---------------------------------------------------------------------------


def test_run_query_sync_stores_result_in_redis():
    """Successful query stores columns, rows, and status in Redis."""
    mock_client = MagicMock()
    mock_session = MagicMock()

    # Simulate a query returning 2 rows
    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "name"]
    mock_result.__iter__ = lambda self: iter([(1, "Alice"), (2, "Bob")])
    mock_session.execute.return_value = mock_result

    with (
        patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client),
        patch("datapulse.core.db_session.open_tenant_session", return_value=mock_session),
    ):
        from datapulse.tasks.async_executor import _run_query_sync

        _run_query_sync("j1", "SELECT 1", None, "1", 100)

    # Verify the final Redis write contains 'complete' status
    calls = mock_client.setex.call_args_list
    last_call_data = json.loads(calls[-1][0][2])
    assert last_call_data["status"] == "complete"
    assert last_call_data["row_count"] == 2


def test_run_query_sync_handles_query_error():
    """Query failure stores error status in Redis."""
    import sqlalchemy.exc

    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.execute.side_effect = sqlalchemy.exc.OperationalError(
        "SELECT bad", {}, Exception("column not found")
    )

    with (
        patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client),
        patch("datapulse.core.db_session.open_tenant_session", return_value=mock_session),
    ):
        from datapulse.tasks.async_executor import _run_query_sync

        _run_query_sync("j-err", "SELECT bad", None, "1", 100)

    calls = mock_client.setex.call_args_list
    last_call_data = json.loads(calls[-1][0][2])
    assert last_call_data["status"] == "failed"
    assert "column not found" in last_call_data["error"]


# ---------------------------------------------------------------------------
# submit_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_query_returns_none_when_no_redis():
    """Returns None when Redis is unavailable."""
    with patch("datapulse.tasks.async_executor._get_job_client", return_value=None):
        from datapulse.tasks.async_executor import submit_query

        result = await submit_query("SELECT 1")
        assert result is None


@pytest.mark.asyncio
async def test_submit_query_returns_job_id():
    """Returns a UUID job_id when Redis is available."""
    mock_client = MagicMock()

    with (
        patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client),
        patch("datapulse.tasks.async_executor._reserve_query_slot") as mock_reserve,
        patch("datapulse.tasks.async_executor.asyncio") as mock_asyncio,
    ):
        mock_loop = MagicMock()
        mock_asyncio.get_event_loop.return_value = mock_loop

        from datapulse.tasks.async_executor import submit_query

        job_id = await submit_query("SELECT 1", tenant_id="1")

        assert job_id is not None
        assert len(job_id) == 36  # UUID format
        mock_reserve.assert_called_once_with("1")
        mock_loop.run_in_executor.assert_called_once()


@pytest.mark.asyncio
async def test_submit_query_rejects_when_capacity_is_full():
    """Executor should reject new heavy jobs when all local slots are in use."""
    mock_client = MagicMock()

    with (
        patch("datapulse.tasks.async_executor._get_job_client", return_value=mock_client),
        patch(
            "datapulse.tasks.async_executor._reserve_query_slot",
            side_effect=QueryCapacityExceededError("busy"),
        ),
    ):
        from datapulse.tasks.async_executor import submit_query

        with pytest.raises(QueryCapacityExceededError, match="busy"):
            await submit_query("SELECT 1", tenant_id="1")


def test_run_query_job_sync_releases_reserved_slot():
    """Reserved capacity must be released even when job execution fails."""
    with (
        patch(
            "datapulse.tasks.async_executor._run_query_sync",
            side_effect=RuntimeError("boom"),
        ),
        patch("datapulse.tasks.async_executor._release_query_slot") as mock_release,
    ):
        from datapulse.tasks.async_executor import _run_query_job_sync

        with pytest.raises(RuntimeError, match="boom"):
            _run_query_job_sync("job-1", "SELECT 1", None, "7", 25)

        mock_release.assert_called_once_with("7")
