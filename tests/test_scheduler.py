"""Tests for datapulse.scheduler — pipeline orchestration and scheduled jobs."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
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
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.executor.PipelineExecutor") as mock_executor_cls,
        patch("datapulse.pipeline.repository.PipelineRepository"),
        patch("datapulse.pipeline.quality_repository.QualityRepository"),
        patch("datapulse.pipeline.quality_service.QualityService") as mock_qs_cls,
        patch("datapulse.billing.service.BillingService"),
        patch("datapulse.billing.stripe_client.StripeClient"),
        patch("datapulse.notifications.notify_pipeline_success") as mock_notify_ok,
        patch("datapulse.notifications.notify_pipeline_failure"),
        patch("datapulse.cache.cache_invalidate_pattern"),
    ):
        mock_settings.return_value = MagicMock()

        # Session factory
        mock_session = MagicMock()
        # get_session_factory()() returns a session
        mock_sf.return_value = MagicMock(return_value=mock_session)
        # pg_try_advisory_lock returns True
        mock_session.execute.return_value.scalar.return_value = True

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
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.executor.PipelineExecutor") as mock_executor_cls,
        patch("datapulse.pipeline.repository.PipelineRepository"),
        patch("datapulse.billing.service.BillingService"),
        patch("datapulse.billing.stripe_client.StripeClient"),
        patch("datapulse.notifications.notify_pipeline_success") as mock_ok,
        patch("datapulse.notifications.notify_pipeline_failure") as mock_fail,
        patch("datapulse.cache.cache_invalidate_pattern"),
    ):
        mock_settings.return_value = MagicMock()
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        mock_session.execute.return_value.scalar.return_value = True
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
        patch("datapulse.checks.check_db", return_value={"status": "ok", "latency_ms": 5}),
        patch(
            "datapulse.checks.check_redis",
            return_value={"status": "ok", "latency_ms": 2},
        ),
        patch("datapulse.notifications.notify_health_failure") as mock_notify,
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.repository.PipelineRepository") as mock_repo_cls,
    ):
        # Stale run detection — no stale runs
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        mock_repo_cls.return_value.mark_stale_runs_failed.return_value = []

        from datapulse.scheduler import _health_check

        await _health_check()
        mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_db_failure_notifies():
    """Notification sent when DB is down."""
    with (
        patch(
            "datapulse.checks.check_db",
            return_value={"status": "error", "error": "timeout"},
        ),
        patch("datapulse.checks.check_redis", return_value={"status": "ok"}),
        patch("datapulse.notifications.notify_health_failure") as mock_notify,
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.repository.PipelineRepository") as mock_repo_cls,
    ):
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        mock_repo_cls.return_value.mark_stale_runs_failed.return_value = []

        from datapulse.scheduler import _health_check

        await _health_check()
        mock_notify.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_detects_stale_pipeline():
    """Stale pipeline runs are marked failed and notified."""
    with (
        patch("datapulse.checks.check_db", return_value={"status": "ok", "latency_ms": 5}),
        patch(
            "datapulse.checks.check_redis",
            return_value={"status": "ok", "latency_ms": 2},
        ),
        patch("datapulse.notifications.notify_health_failure"),
        patch("datapulse.notifications.notify_pipeline_failure") as mock_pipe_fail,
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.repository.PipelineRepository") as mock_repo_cls,
    ):
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        stale_id = str(uuid4())
        mock_repo_cls.return_value.mark_stale_runs_failed.return_value = [stale_id]

        from datapulse.scheduler import _health_check

        await _health_check()
        mock_pipe_fail.assert_called_once_with(stale_id, "stale", "Stale: heartbeat timeout")


# ---------------------------------------------------------------------------
# _quality_digest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quality_digest_no_runs():
    """No notification when no pipeline runs exist."""
    with (
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.repository.PipelineRepository") as mock_repo_cls,
        patch("datapulse.notifications.notify_quality_digest") as mock_notify,
    ):
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        mock_repo_cls.return_value.get_latest_run.return_value = None

        from datapulse.scheduler import _quality_digest

        await _quality_digest()
        mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# start_scheduler / stop_scheduler
# ---------------------------------------------------------------------------


def test_start_scheduler_adds_jobs_and_starts():
    """start_scheduler registers 4 jobs and starts the scheduler."""
    with (
        patch("datapulse.scheduler.scheduler") as mock_sched,
        patch("datapulse.scheduler._register_sync_schedules", return_value=0),
    ):
        mock_sched.running = False

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        # 4 static jobs: health_check, quality_digest, ai_digest, rls_audit (#546).
        assert mock_sched.add_job.call_count == 4
        registered_ids = {call.kwargs["id"] for call in mock_sched.add_job.call_args_list}
        assert registered_ids == {"health_check", "quality_digest", "ai_digest", "rls_audit"}
        mock_sched.start.assert_called_once()


def test_start_scheduler_noop_when_running():
    """start_scheduler does nothing if already running."""
    with (
        patch("datapulse.scheduler.scheduler") as mock_sched,
        patch("datapulse.scheduler._register_sync_schedules", return_value=0),
    ):
        mock_sched.running = True

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        mock_sched.add_job.assert_not_called()
        mock_sched.start.assert_not_called()


def test_stop_scheduler_shuts_down():
    """stop_scheduler shuts down the scheduler."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True

        from datapulse.scheduler import stop_scheduler

        stop_scheduler()

        mock_sched.shutdown.assert_called_once_with(wait=False)


def test_stop_scheduler_noop_when_not_running():
    """stop_scheduler does nothing if scheduler is not running."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = False

        from datapulse.scheduler import stop_scheduler

        stop_scheduler()

        mock_sched.shutdown.assert_not_called()


# ---------------------------------------------------------------------------
# get_scheduler_status
# ---------------------------------------------------------------------------


def test_get_scheduler_status_running():
    """Returns running=True with job list when scheduler is running."""
    mock_job = MagicMock()
    mock_job.id = "health_check"
    mock_job.next_run_time = "2026-04-11T12:00:00"

    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True
        mock_sched.get_jobs.return_value = [mock_job]

        from datapulse.scheduler import get_scheduler_status

        status = get_scheduler_status()

        assert status["running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "health_check"


def test_get_scheduler_status_not_running():
    """Returns running=False and no jobs when scheduler is stopped."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = False

        from datapulse.scheduler import get_scheduler_status

        status = get_scheduler_status()

        assert status["running"] is False
        assert status["jobs"] == []


# ---------------------------------------------------------------------------
# Session leak prevention (Layer 1 crash prevention)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_lock_not_acquired_closes_session():
    """lock_session is always closed even when advisory lock is not acquired."""
    run_id = uuid4()

    with (
        patch("datapulse.scheduler.get_settings") as mock_settings,
        patch("datapulse.core.db.get_session_factory") as mock_sf,
        patch("datapulse.pipeline.repository.PipelineRepository"),
        patch("datapulse.notifications.notify_pipeline_failure"),
        patch("datapulse.cache.cache_invalidate_pattern"),
    ):
        mock_settings.return_value = MagicMock()
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        # Advisory lock returns False — another pipeline is running
        mock_session.execute.return_value.scalar.return_value = False

        from datapulse.scheduler import run_pipeline

        await run_pipeline(run_id=run_id, source_dir="/data")

        # Session MUST be closed even on early return
        mock_session.close.assert_called()


# ---------------------------------------------------------------------------
# Scheduler SCHEDULER_ENABLED gate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_start_scheduler_skipped_when_disabled():
    """start_scheduler does nothing when SCHEDULER_ENABLED=false."""
    with (
        patch.dict(os.environ, {"SCHEDULER_ENABLED": "false"}),
        patch("datapulse.scheduler.scheduler") as mock_sched,
    ):
        mock_sched.running = False

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        mock_sched.add_job.assert_not_called()
        mock_sched.start.assert_not_called()


@pytest.mark.unit
def test_start_scheduler_enabled_by_default():
    """start_scheduler runs when SCHEDULER_ENABLED is not set (defaults to true)."""
    env = os.environ.copy()
    env.pop("SCHEDULER_ENABLED", None)

    with (
        patch.dict(os.environ, env, clear=True),
        patch("datapulse.scheduler.scheduler") as mock_sched,
        patch("datapulse.scheduler._register_sync_schedules", return_value=0),
    ):
        mock_sched.running = False

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        # 4 static jobs incl. rls_audit (#546).
        assert mock_sched.add_job.call_count == 4
        mock_sched.start.assert_called_once()
