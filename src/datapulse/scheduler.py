"""Pipeline orchestrator and scheduler.

Replaces n8n with a lightweight in-process scheduler using APScheduler.
Runs inside the API process — no extra containers needed.

Scheduled jobs:
- Health check: every 5 minutes
- Quality digest: daily at 18:00 UTC
- AI insights digest: daily at 09:00 UTC

On-demand:
- run_pipeline(): full Bronze → Silver → Gold → Forecasting with quality gates
"""

from __future__ import annotations

import asyncio
import time
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from structlog.contextvars import bind_contextvars, clear_contextvars

from datapulse.config import get_settings
from datapulse.logging import get_logger

log = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


# ---------------------------------------------------------------------------
# Pipeline orchestrator (replaces n8n 2.3.1)
# ---------------------------------------------------------------------------


async def run_pipeline(
    run_id: UUID,
    source_dir: str,
    tenant_id: int = 1,
) -> None:
    """Execute full pipeline: Bronze → Quality → Silver → Quality → Gold → Quality → Forecasting.

    Runs each stage via the PipelineExecutor (in a thread), checks quality
    gates between stages, and updates run status in the database.
    """
    from sqlalchemy import text as sa_text

    from datapulse.cache import cache_invalidate_pattern
    from datapulse.core.db import get_session_factory
    from datapulse.notifications import notify_pipeline_failure, notify_pipeline_success
    from datapulse.pipeline.executor import PipelineExecutor
    from datapulse.pipeline.models import PipelineRunUpdate
    from datapulse.pipeline.quality_repository import QualityRepository
    from datapulse.pipeline.quality_service import QualityService
    from datapulse.pipeline.repository import PipelineRepository

    settings = get_settings()
    executor = PipelineExecutor(settings=settings)
    run_id_str = str(run_id)
    t0 = time.perf_counter()
    bind_contextvars(run_id=run_id_str, tenant_id=str(tenant_id))

    def _get_session():
        session = get_session_factory()()
        session.execute(sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        session.execute(sa_text("SET LOCAL statement_timeout = '600s'"))
        return session

    def _update_status(status: str, error_message: str | None = None, rows: int | None = None):
        session = _get_session()
        try:
            repo = PipelineRepository(session)
            update = PipelineRunUpdate(status=status, error_message=error_message, rows_loaded=rows)
            repo.update_run(run_id, update)
            session.commit()
        finally:
            session.close()

    def _quality_check(stage: str) -> bool:
        session = _get_session()
        try:
            q_repo = QualityRepository(session)
            q_svc = QualityService(q_repo, session, settings)
            report = q_svc.run_checks_for_stage(run_id=run_id, stage=stage, tenant_id=tenant_id)
            session.commit()
            return report.gate_passed
        finally:
            session.close()

    stages = [
        ("running", "bronze", lambda: executor.run_bronze(run_id=run_id, source_dir=source_dir)),
        ("bronze_complete", "bronze", None),  # quality check
        (None, "dbt-staging", lambda: executor.run_dbt(run_id=run_id, selector="staging")),
        ("silver_complete", "silver", None),  # quality check
        (None, "dbt-marts", lambda: executor.run_dbt(run_id=run_id, selector="marts")),
        ("gold_complete", "gold", None),  # quality check
        (
            None,
            "forecasting",
            lambda: executor.run_forecasting(run_id=run_id, tenant_id=str(tenant_id)),
        ),
    ]

    log.info("pipeline_start", run_id=run_id_str)

    # Acquire advisory lock to prevent concurrent pipeline runs
    lock_session = get_session_factory()()
    try:
        lock_result = lock_session.execute(sa_text("SELECT pg_try_advisory_lock(42)")).scalar()
        if not lock_result:
            log.warning("pipeline_already_running", run_id=run_id_str)
            _update_status("failed", error_message="Another pipeline is already running")
            notify_pipeline_failure(run_id_str, "lock", "Another pipeline is already running")
            return
    except Exception:
        lock_session.close()
        raise

    _update_status("running")
    total_rows = 0

    try:
        for status_name, stage, execute_fn in stages:
            if execute_fn:
                # Execute stage in thread
                result = await asyncio.to_thread(execute_fn)
                if not result.success:
                    _update_status("failed", error_message=result.error)
                    notify_pipeline_failure(run_id_str, stage, result.error or "Unknown error")
                    log.error(
                        "pipeline_stage_failed", run_id=run_id_str, stage=stage, error=result.error
                    )
                    return
                if result.rows_loaded:
                    total_rows = result.rows_loaded
                log.info(
                    "pipeline_stage_done",
                    run_id=run_id_str,
                    stage=stage,
                    duration=result.duration_seconds,
                )
            elif status_name:
                # Update status + run quality check
                _update_status(status_name)
                gate_passed = await asyncio.to_thread(_quality_check, stage)
                if not gate_passed:
                    error_msg = f"Quality gate failed at {stage} stage"
                    _update_status("failed", error_message=error_msg)
                    notify_pipeline_failure(run_id_str, stage, error_msg)
                    log.error("pipeline_quality_gate_failed", run_id=run_id_str, stage=stage)
                    return
                log.info("pipeline_quality_gate_passed", run_id=run_id_str, stage=stage)

        # All stages complete
        elapsed = round(time.perf_counter() - t0, 2)
        _update_status("success", rows=total_rows)
        cache_invalidate_pattern("datapulse:analytics:*")
        notify_pipeline_success(run_id_str, elapsed, total_rows)
        log.info("pipeline_complete", run_id=run_id_str, duration=elapsed, rows=total_rows)

    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        error_msg = str(exc)[:200]
        _update_status("failed", error_message=error_msg)
        notify_pipeline_failure(run_id_str, "unknown", error_msg)
        log.error("pipeline_crashed", run_id=run_id_str, error=error_msg, duration=elapsed)
    finally:
        # Release advisory lock
        try:
            lock_session.execute(sa_text("SELECT pg_advisory_unlock(42)"))
            lock_session.commit()
        except Exception:
            pass
        finally:
            lock_session.close()
        clear_contextvars()


# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------


async def _health_check() -> None:
    """Check API health every 5 minutes (replaces n8n 2.1.1)."""
    from datapulse.api.routes.health import _check_db, _check_redis

    db = _check_db()
    redis = _check_redis()

    if db["status"] != "ok":
        from datapulse.notifications import notify_health_failure

        notify_health_failure(db["status"], db.get("error", "unknown"))
        log.error("health_check_failed", component="database", status=db["status"])
    elif redis["status"] not in ("ok", "disabled"):
        from datapulse.notifications import notify_health_failure

        notify_health_failure(redis["status"], redis.get("error", "unknown"))
        log.error("health_check_failed", component="redis", status=redis["status"])
    else:
        log.debug("health_check_ok", db_latency=db.get("latency_ms"))


async def _quality_digest() -> None:
    """Send daily quality digest at 18:00 UTC (replaces n8n 2.6.3)."""
    from sqlalchemy import text as sa_text

    from datapulse.core.db import get_session_factory
    from datapulse.notifications import notify_quality_digest
    from datapulse.pipeline.quality_repository import QualityRepository
    from datapulse.pipeline.repository import PipelineRepository

    session = get_session_factory()()
    try:
        session.execute(sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": "1"})
        repo = PipelineRepository(session)
        latest = repo.get_latest_run()
        if not latest:
            log.info("quality_digest_no_runs")
            return

        q_repo = QualityRepository(session)
        checks = q_repo.get_checks_for_run(latest.id)

        total = len(checks.items) if checks else 0
        passed = len([c for c in (checks.items if checks else []) if c.passed])

        notify_quality_digest(
            run_id=str(latest.id),
            status=latest.status,
            total_checks=total,
            checks_passed=passed,
        )
        log.info("quality_digest_sent", run_id=str(latest.id))
    except Exception as exc:
        log.error("quality_digest_failed", error=str(exc))
    finally:
        session.close()


async def _ai_digest() -> None:
    """Send daily AI insights digest at 09:00 UTC (replaces n8n 2.8.1)."""
    import httpx

    from datapulse.notifications import notify_ai_digest

    settings = get_settings()
    api_base = (
        f"http://localhost:{settings.api_port}"
        if hasattr(settings, "api_port")
        else "http://localhost:8000"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if AI is available
            status_resp = await client.get(f"{api_base}/api/v1/ai-light/status")
            if not status_resp.json().get("available", False):
                log.info("ai_digest_skipped", reason="AI not available")
                return

            # Get summary + anomalies
            summary_resp = await client.get(f"{api_base}/api/v1/ai-light/summary")
            anomalies_resp = await client.get(f"{api_base}/api/v1/ai-light/anomalies")

            summary = summary_resp.json()
            anomalies = anomalies_resp.json()

            notify_ai_digest(
                narrative=summary.get("narrative", "No summary available"),
                highlights=summary.get("highlights", []),
                anomaly_count=len(anomalies.get("anomalies", [])),
            )
            log.info("ai_digest_sent")
    except Exception as exc:
        log.error("ai_digest_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


def start_scheduler() -> None:
    """Start the background scheduler with all jobs."""
    if scheduler.running:
        return

    scheduler.add_job(
        _health_check, IntervalTrigger(minutes=5), id="health_check", replace_existing=True
    )
    scheduler.add_job(
        _quality_digest, CronTrigger(hour=18, minute=0), id="quality_digest", replace_existing=True
    )
    scheduler.add_job(
        _ai_digest, CronTrigger(hour=9, minute=0), id="ai_digest", replace_existing=True
    )

    scheduler.start()
    log.info(
        "scheduler_started", jobs=["health_check(5m)", "quality_digest(18:00)", "ai_digest(09:00)"]
    )


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
