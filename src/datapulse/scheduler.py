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
from sqlalchemy import text as sa_text
from structlog.contextvars import bind_contextvars, clear_contextvars

from datapulse.config import get_settings
from datapulse.logging import get_logger
from datapulse.metrics import (
    pipeline_duration_seconds,
    pipeline_runs_total,
    pipeline_stale_detected,
    scheduler_jobs_executed,
)

log = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


# ---------------------------------------------------------------------------
# Pipeline orchestrator (replaces n8n 2.3.1)
# ---------------------------------------------------------------------------


_STAGE_ORDER = ["bronze", "dbt-staging", "silver", "dbt-marts", "gold", "forecasting"]


def _stage_index(stage: str) -> int:
    """Return the ordinal position of a stage name, or -1 if unknown."""
    try:
        return _STAGE_ORDER.index(stage)
    except ValueError:
        return -1


async def run_pipeline(
    run_id: UUID,
    source_dir: str,
    tenant_id: int = 1,
    resume_from: str | None = None,
) -> None:
    """Execute full pipeline: Bronze → Quality → Silver → Quality → Gold → Quality → Forecasting.

    Runs each stage via the PipelineExecutor (in a thread), checks quality
    gates between stages, and updates run status in the database.

    Args:
        run_id: UUID of the existing pipeline_runs record to update.
        source_dir: Path to raw source files for the bronze loader.
        tenant_id: Tenant scoping for RLS and notifications.
        resume_from: Stage name to resume from (skips all prior stages).
            Valid values: "bronze", "dbt-staging", "dbt-marts", "forecasting".
    """
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

    def _update_status(
        status: str,
        error_message: str | None = None,
        rows: int | None = None,
        last_completed_stage: str | None = None,
    ) -> None:
        session = _get_session()
        try:
            repo = PipelineRepository(session)
            update = PipelineRunUpdate(
                status=status,
                error_message=error_message,
                rows_loaded=rows,
                last_completed_stage=last_completed_stage,
            )
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

    def _heartbeat() -> None:
        """Update heartbeat_at to signal the pipeline is still alive."""
        session = _get_session()
        try:
            repo = PipelineRepository(session)
            repo.update_heartbeat(run_id)
        except Exception:
            log.warning("pipeline_heartbeat_failed", run_id=run_id_str, exc_info=True)
        finally:
            session.close()

    def _update_usage(tid: int, rows_loaded: int) -> None:
        """Update usage_metrics after a successful pipeline run."""
        from sqlalchemy.exc import SQLAlchemyError

        from datapulse.billing.repository import BillingRepository

        session = _get_session()
        try:
            billing_repo = BillingRepository(session)
            # Count distinct data sources for this tenant
            source_count_row = session.execute(
                sa_text(
                    "SELECT COUNT(DISTINCT source_file) FROM bronze.sales WHERE tenant_id = :tid"
                ),
                {"tid": tid},
            ).scalar()
            # Count total rows for this tenant
            row_count = session.execute(
                sa_text("SELECT COUNT(*) FROM bronze.sales WHERE tenant_id = :tid"),
                {"tid": tid},
            ).scalar()

            billing_repo.upsert_usage(
                tid,
                data_sources_count=source_count_row or 0,
                total_rows=row_count or rows_loaded,
            )
            session.commit()
            log.info(
                "usage_metrics_updated",
                tenant_id=tid,
                data_sources=source_count_row,
                total_rows=row_count or rows_loaded,
            )
        except SQLAlchemyError:
            session.rollback()
            log.error("usage_metrics_update_failed", tenant_id=tid, exc_info=True)
        finally:
            session.close()

    def _check_plan_limits_under_lock(tid: int) -> str | None:
        """Re-validate plan limits under advisory lock (TOCTOU defense).

        Returns None if OK, or an error message if limits are exceeded.
        """
        from datapulse.billing.repository import BillingRepository
        from datapulse.billing.service import BillingService, PlanLimitExceededError
        from datapulse.billing.stripe_client import StripeClient

        session = _get_session()
        try:
            billing_repo = BillingRepository(session)
            client = StripeClient(settings.stripe_secret_key)
            billing_svc = BillingService(
                billing_repo,
                client,
                price_to_plan=settings.stripe_price_to_plan_map,
                base_url=settings.billing_base_url,
            )
            billing_svc.check_plan_limits(tid)
            return None
        except PlanLimitExceededError as e:
            return str(e)
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

    # Re-validate plan limits under lock (TOCTOU defense)
    limit_error = await asyncio.to_thread(_check_plan_limits_under_lock, tenant_id)
    if limit_error:
        _update_status("failed", error_message=f"Plan limit exceeded: {limit_error}")
        notify_pipeline_failure(run_id_str, "plan_check", limit_error)
        log.warning("pipeline_plan_limit_exceeded", run_id=run_id_str, tenant_id=tenant_id)
        # Release lock early
        try:
            lock_session.execute(sa_text("SELECT pg_advisory_unlock(42)"))
            lock_session.commit()
        finally:
            lock_session.close()
        clear_contextvars()
        return

    _update_status("running")
    await asyncio.to_thread(_heartbeat)  # initial heartbeat
    total_rows = 0
    resume_idx = _stage_index(resume_from) if resume_from else -1

    try:
        for status_name, stage, execute_fn in stages:
            # Skip stages before resume_from when resuming a partial run
            if resume_from and _stage_index(stage) < resume_idx:
                log.info(
                    "pipeline_stage_skipped",
                    run_id=run_id_str,
                    stage=stage,
                    reason=f"resume_from={resume_from}",
                )
                continue

            # Heartbeat between stages so stale-detection knows we're alive
            await asyncio.to_thread(_heartbeat)

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
                _update_status("running", last_completed_stage=stage)
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

        # Update usage metrics for billing enforcement (in thread — avoids blocking event loop)
        await asyncio.to_thread(_update_usage, tenant_id, total_rows)

        notify_pipeline_success(run_id_str, elapsed, total_rows)
        pipeline_runs_total.labels(status="success").inc()
        pipeline_duration_seconds.observe(elapsed)
        log.info("pipeline_complete", run_id=run_id_str, duration=elapsed, rows=total_rows)

    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        error_msg = str(exc)[:200]
        _update_status("failed", error_message=error_msg)
        notify_pipeline_failure(run_id_str, "unknown", error_msg)
        pipeline_runs_total.labels(status="failed").inc()
        pipeline_duration_seconds.observe(elapsed)
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
    scheduler_jobs_executed.labels(job="health_check").inc()
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

    # Detect and clean up stale pipeline runs (heartbeat > 10 min old)
    try:
        from datapulse.core.db import get_session_factory
        from datapulse.notifications import notify_pipeline_failure
        from datapulse.pipeline.repository import PipelineRepository

        session = get_session_factory()()
        try:
            session.execute(sa_text("SET LOCAL app.tenant_id = '1'"))
            repo = PipelineRepository(session)
            stale_ids = repo.mark_stale_runs_failed(stale_minutes=10)
            if stale_ids:
                for sid in stale_ids:
                    notify_pipeline_failure(sid, "stale", "Stale: heartbeat timeout")
                    pipeline_stale_detected.inc()
                log.warning("pipeline_stale_detected", stale_run_ids=stale_ids)
        finally:
            session.close()
    except Exception:
        log.warning("stale_run_detection_failed", exc_info=True)


async def _quality_digest() -> None:
    """Send daily quality digest at 18:00 UTC (replaces n8n 2.6.3)."""
    scheduler_jobs_executed.labels(job="quality_digest").inc()
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
    scheduler_jobs_executed.labels(job="ai_digest").inc()
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
    """Start the background scheduler with all jobs.

    Called once per uvicorn worker.  With ``--workers N`` every worker runs
    its own scheduler instance — jobs are idempotent so duplication is
    harmless.  Leader election (advisory-lock based) was removed because
    the DB session it opened during lifespan startup deadlocked the
    forked workers in production (all stuck at "Waiting for application
    startup").  Re-add leader election as a post-startup background task
    if single-execution is needed.
    """
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
        "scheduler_started",
        jobs=["health_check(5m)", "quality_digest(18:00)", "ai_digest(09:00)"],
    )


def get_scheduler_status() -> dict:
    """Return scheduler status for the health endpoint."""
    return {
        "running": scheduler.running,
        "jobs": [{"id": job.id, "next_run": str(job.next_run_time)} for job in scheduler.get_jobs()]
        if scheduler.running
        else [],
    }


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
