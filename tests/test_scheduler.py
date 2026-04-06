"""Tests for datapulse.scheduler — pipeline orchestration and scheduled jobs."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_pipeline_success():
    """Full pipeline completes when all stages succeed and gates pass."""
    run_id = uuid4()
    mock_result = MagicMock(success=True, error=None, rows_loaded=1000, duration_seconds=5.0)

    with (
        patch("datapulse.scheduler.get_settings") as mock_settings,
        patch("datapulse.scheduler.get_session_factory") as mock_sf,
        patch("datapulse.scheduler.PipelineExecutor") as mock_executor_cls,
        patch("datapulse.scheduler.PipelineRepository"),
        patch("datapulse.scheduler.QualityRepository"),
        patch("datapulse.scheduler.QualityService") as mock_qs_cls,
        patch("datapulse.scheduler.notify_pipeline_success") as mock_notify_ok,
        patch("datapulse.scheduler.notify_pipeline_failure"),
        patch("datapulse.scheduler.cache_invalidate_pattern"),
    ):
        mock_settings.return_value = MagicMock()

        # Session factory
        mock_session = MagicMock()
        mock_sf.return_value = lambda: mock_session

        # Executor stages all succeed
        mock_executor = mock_executor_cls.return_value
        mock_executor.run_bronze.return_value = mock_result
        mock_executor.run_dbt.return_value = mock_result
        mock_executor.run_forecasting.return_value = mock_result

        # Quality gates all pass
        mock_report = MagicMock(gate_passed=True)
        mock_qs_cls.return_value.run_checks_for_stage.return_value = mock_report

        from datapulse.scheduler import run_pipeline

        await run_pipeline(run_id=run_id, source_dir="/data")

        mock_notify_ok.assert_called_once()


@pytest.mark.asyncio
async def test_run_pipeline_stage_failure_stops_pipeline():
    """Pipeline stops and notifies on stage failure."""
    run_id = uuid4()
    fail_result = MagicMock(success=False, error="Bronze exploded", rows_loaded=None)

    with (
        patch("datapulse.scheduler.get_settings") as mock_settings,
        patch("datapulse.scheduler.get_session_factory") as mock_sf,
        patch("datapulse.scheduler.PipelineExecutor") as mock_executor_cls,
        patch("datapulse.scheduler.PipelineRepository"),
        patch("datapulse.scheduler.notify_pipeline_success") as mock_ok,
        patch("datapulse.scheduler.notify_pipeline_failure") as mock_fail,
        patch("datapulse.scheduler.cache_invalidate_pattern"),
    ):
        mock_settings.return_value = MagicMock()
        mock_session = MagicMock()
        mock_sf.return_value = lambda: mock_session
        mock_executor_cls.return_value.run_bronze.return_value = fail_result

        from datapulse.scheduler import run_pipeline

        await run_pipeline(run_id=run_id, source_dir="/data")

        mock_fail.assert_called_once()
        mock_ok.assert_not_called()


# ---------------------------------------------------------------------------
# _health_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_all_ok():
    """No notification when DB and Redis are healthy."""
    with (
        patch("datapulse.scheduler._check_db", return_value={"status": "ok", "latency_ms": 5}),
        patch("datapulse.scheduler._check_redis", return_value={"status": "ok", "latency_ms": 2}),
        patch("datapulse.scheduler.notify_health_failure") as mock_notify,
    ):
        from datapulse.scheduler import _health_check

        await _health_check()
        mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_db_failure_notifies():
    """Notification sent when DB is down."""
    with (
        patch("datapulse.scheduler._check_db", return_value={"status": "error", "error": "timeout"}),
        patch("datapulse.scheduler._check_redis", return_value={"status": "ok"}),
        patch("datapulse.scheduler.notify_health_failure") as mock_notify,
    ):
        from datapulse.scheduler import _health_check

        await _health_check()
        mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# _quality_digest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quality_digest_no_runs():
    """No notification when no pipeline runs exist."""
    with (
        patch("datapulse.scheduler.get_session_factory") as mock_sf,
        patch("datapulse.scheduler.PipelineRepository") as mock_repo_cls,
        patch("datapulse.scheduler.notify_quality_digest") as mock_notify,
    ):
        mock_session = MagicMock()
        mock_sf.return_value = lambda: mock_session
        mock_repo_cls.return_value.get_latest_run.return_value = None

        from datapulse.scheduler import _quality_digest

        await _quality_digest()
        mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# start_scheduler / stop_scheduler
# ---------------------------------------------------------------------------


def test_start_scheduler_registers_jobs():
    """start_scheduler adds 3 jobs to the APScheduler instance."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = False

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        assert mock_sched.add_job.call_count == 3
        mock_sched.start.assert_called_once()


def test_start_scheduler_noop_when_running():
    """start_scheduler does nothing if already running."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        mock_sched.add_job.assert_not_called()
        mock_sched.start.assert_not_called()


def test_stop_scheduler():
    """stop_scheduler shuts down a running scheduler."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True

        from datapulse.scheduler import stop_scheduler

        stop_scheduler()

        mock_sched.shutdown.assert_called_once_with(wait=False)
