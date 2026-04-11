"""Tests for datapulse.scheduler — pipeline orchestration and scheduled jobs."""

from __future__ import annotations

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
        patch(
            "datapulse.api.routes.health._check_db", return_value={"status": "ok", "latency_ms": 5}
        ),
        patch(
            "datapulse.api.routes.health._check_redis",
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
            "datapulse.api.routes.health._check_db",
            return_value={"status": "error", "error": "timeout"},
        ),
        patch("datapulse.api.routes.health._check_redis", return_value={"status": "ok"}),
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
        patch(
            "datapulse.api.routes.health._check_db", return_value={"status": "ok", "latency_ms": 5}
        ),
        patch(
            "datapulse.api.routes.health._check_redis",
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
# start_scheduler / stop_scheduler — leader election
# ---------------------------------------------------------------------------


def test_start_scheduler_acquires_lock_and_starts():
    """start_scheduler starts APScheduler when advisory lock is acquired."""
    with (
        patch("datapulse.scheduler.scheduler") as mock_sched,
        patch("datapulse.core.db.get_session_factory") as mock_sf,
    ):
        mock_sched.running = False
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        # Advisory lock succeeds
        mock_session.execute.return_value.scalar.return_value = True

        import datapulse.scheduler as sched_mod

        sched_mod._lock_session = None
        sched_mod.start_scheduler()

        assert mock_sched.add_job.call_count == 3
        mock_sched.start.assert_called_once()
        assert sched_mod._lock_session is mock_session


def test_start_scheduler_skips_when_lock_held():
    """start_scheduler skips silently when another worker holds the lock."""
    with (
        patch("datapulse.scheduler.scheduler") as mock_sched,
        patch("datapulse.core.db.get_session_factory") as mock_sf,
    ):
        mock_sched.running = False
        mock_session = MagicMock()
        mock_sf.return_value = MagicMock(return_value=mock_session)
        # Advisory lock denied — another worker has it
        mock_session.execute.return_value.scalar.return_value = False

        import datapulse.scheduler as sched_mod

        sched_mod._lock_session = None
        sched_mod.start_scheduler()

        mock_sched.start.assert_not_called()
        mock_session.close.assert_called_once()
        assert sched_mod._lock_session is None


def test_start_scheduler_noop_when_running():
    """start_scheduler does nothing if already running."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True

        from datapulse.scheduler import start_scheduler

        start_scheduler()

        mock_sched.add_job.assert_not_called()
        mock_sched.start.assert_not_called()


def test_stop_scheduler_releases_lock():
    """stop_scheduler shuts down and releases the advisory lock."""
    mock_lock_session = MagicMock()

    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True

        import datapulse.scheduler as sched_mod

        sched_mod._lock_session = mock_lock_session
        sched_mod.stop_scheduler()

        mock_sched.shutdown.assert_called_once_with(wait=False)
        # Lock should be released and session closed
        assert mock_lock_session.execute.called
        assert mock_lock_session.commit.called
        assert mock_lock_session.close.called
        assert sched_mod._lock_session is None


def test_stop_scheduler_no_lock():
    """stop_scheduler works without a lock session (non-leader worker)."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True

        import datapulse.scheduler as sched_mod

        sched_mod._lock_session = None
        sched_mod.stop_scheduler()

        mock_sched.shutdown.assert_called_once_with(wait=False)
        # No lock to release — should not raise
        assert sched_mod._lock_session is None


# ---------------------------------------------------------------------------
# get_scheduler_status
# ---------------------------------------------------------------------------


def test_get_scheduler_status_leader():
    """Returns leader=True with job list when scheduler is running."""
    mock_job = MagicMock()
    mock_job.id = "health_check"
    mock_job.next_run_time = "2026-04-11T12:00:00"

    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = True
        mock_sched.get_jobs.return_value = [mock_job]

        import datapulse.scheduler as sched_mod

        sched_mod._lock_session = MagicMock()  # has lock = is leader
        status = sched_mod.get_scheduler_status()

        assert status["is_leader"] is True
        assert status["running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "health_check"


def test_get_scheduler_status_not_leader():
    """Returns leader=False and no jobs when not the leader."""
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = False

        import datapulse.scheduler as sched_mod

        sched_mod._lock_session = None
        status = sched_mod.get_scheduler_status()

        assert status["is_leader"] is False
        assert status["running"] is False
        assert status["jobs"] == []
