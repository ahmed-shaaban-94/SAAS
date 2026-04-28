"""Tests for datapulse.tasks.async_executor — Redis-backed query execution."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from datapulse.tasks.async_executor import (
    _query_timeout,
    get_job_result,
)

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
# submit_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_query_returns_none_when_no_redis():
    """Returns None when Redis is unavailable."""
    with patch("datapulse.tasks.async_executor._get_job_client", return_value=None):
        from datapulse.tasks.async_executor import submit_query

        result = await submit_query("SELECT 1")
        assert result is None
