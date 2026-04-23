"""Scheduled job implementations for the DataPulse pipeline scheduler.

Each function is registered as an APScheduler job in start_scheduler().
Extracted from scheduler.py to separate job logic from pipeline orchestration.
"""

from __future__ import annotations

from datapulse.config import get_settings
from datapulse.core.db import plain_session_scope, tenant_session_scope
from datapulse.logging import get_logger
from datapulse.metrics import pipeline_stale_detected, scheduler_jobs_executed

log = get_logger(__name__)


async def _health_check() -> None:
    """Check API health every 5 minutes (replaces n8n 2.1.1)."""
    scheduler_jobs_executed.labels(job="health_check").inc()
    from datapulse.checks import check_db, check_redis

    db = check_db()
    redis = check_redis()

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
        from datapulse.notifications import notify_pipeline_failure
        from datapulse.pipeline.repository import PipelineRepository

        with tenant_session_scope(
            "1",
            statement_timeout="30s",
            session_type="scheduler_health",
        ) as session:
            repo = PipelineRepository(session)
            stale_ids = repo.mark_stale_runs_failed(stale_minutes=10)
            if stale_ids:
                for sid in stale_ids:
                    notify_pipeline_failure(sid, "stale", "Stale: heartbeat timeout")
                    pipeline_stale_detected.inc()
                log.warning("pipeline_stale_detected", stale_run_ids=stale_ids)
    except Exception:
        log.warning("stale_run_detection_failed", exc_info=True)


async def _quality_digest() -> None:
    """Send daily quality digest at 18:00 UTC (replaces n8n 2.6.3)."""
    scheduler_jobs_executed.labels(job="quality_digest").inc()
    from datapulse.notifications import notify_quality_digest
    from datapulse.pipeline.quality_repository import QualityRepository
    from datapulse.pipeline.repository import PipelineRepository

    try:
        with tenant_session_scope(
            "1",
            statement_timeout="30s",
            session_type="quality_digest",
        ) as session:
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


async def _rls_audit() -> None:
    """Assert RLS + FORCE RLS on every marts/staging table (#546).

    dbt post-hooks apply RLS after table creation — if a run crashes in
    between, a table briefly lives without protection. This nightly job
    is the safety net: any missing invariant triggers a Slack alert so
    an operator can re-run dbt or apply RLS manually.
    """
    scheduler_jobs_executed.labels(job="rls_audit").inc()
    from datapulse.notifications import notify_rls_violation
    from datapulse.pipeline.rls_audit import audit_rls_enforcement

    try:
        with plain_session_scope(statement_timeout="30s", session_type="rls_audit") as session:
            violations = audit_rls_enforcement(session)
            if violations:
                fqns = [v.fqn for v in violations]
                log.error("rls_audit_failed", violations=fqns, count=len(fqns))
                notify_rls_violation(fqns)
            else:
                log.info("rls_audit_ok")
    except Exception as exc:
        log.error("rls_audit_error", error=str(exc), exc_info=True)


def _make_sync_job_fn(connection_id: int, tenant_id: int, schedule_id: int):  # type: ignore[return]
    """Return an async coroutine that triggers a scheduled sync and stamps last_run_at."""

    async def _run() -> None:
        from datapulse.control_center.repository import (  # noqa: PLC0415
            MappingTemplateRepository,
            PipelineDraftRepository,
            PipelineProfileRepository,
            PipelineReleaseRepository,
            SourceConnectionRepository,
            SyncJobRepository,
            SyncScheduleRepository,
        )
        from datapulse.control_center.service import ControlCenterService  # noqa: PLC0415

        try:
            with tenant_session_scope(
                tenant_id,
                statement_timeout="30s",
                session_type="scheduler_sync",
            ) as session:
                svc = ControlCenterService(
                    session,
                    connections=SourceConnectionRepository(session),
                    profiles=PipelineProfileRepository(session),
                    mappings=MappingTemplateRepository(session),
                    releases=PipelineReleaseRepository(session),
                    sync_jobs=SyncJobRepository(session),
                    drafts=PipelineDraftRepository(session),
                    schedules=SyncScheduleRepository(session),
                )
                svc.trigger_sync(
                    connection_id,
                    tenant_id=tenant_id,
                    run_mode="scheduled",
                    created_by="scheduler",
                )
                # Stamp last_run_at on the schedule row
                SyncScheduleRepository(session).update_last_run(schedule_id)
                log.info(
                    "scheduled_sync_triggered",
                    connection_id=connection_id,
                    tenant_id=tenant_id,
                    schedule_id=schedule_id,
                )
        except Exception:
            log.error(
                "scheduled_sync_failed",
                connection_id=connection_id,
                tenant_id=tenant_id,
                schedule_id=schedule_id,
                exc_info=True,
            )

    return _run


async def _refresh_cross_sell_rules() -> None:
    """Weekly Market Basket Analysis — update pos.cross_sell_rules from real sales.

    Runs every Sunday at 02:00 UTC. Mines the last 90 days of completed POS
    transactions per tenant and upserts learned cross-sell pairs.
    Zero external API calls — pure SQL on existing data.
    """
    from sqlalchemy import text as sa_text  # noqa: PLC0415

    from datapulse.pos.mba import run_mba  # noqa: PLC0415

    scheduler_jobs_executed.labels(job="mba_cross_sell").inc()

    try:
        with plain_session_scope(session_type="mba_probe") as probe:
            rows = probe.execute(
                sa_text(
                    "SELECT DISTINCT tenant_id FROM pos.transactions "
                    "WHERE status = 'completed' LIMIT 200"
                )
            ).fetchall()
            tenant_ids = [r[0] for r in rows]
    except Exception as exc:
        log.warning("mba_tenant_probe_failed", error=str(exc))
        return

    if not tenant_ids:
        log.info("mba_skipped", reason="no completed POS transactions")
        return

    total_upserted = 0
    for tenant_id in tenant_ids:
        try:
            with tenant_session_scope(str(tenant_id), session_type="mba_run") as session:
                result = run_mba(session, tenant_id)
                total_upserted += result["rules_upserted"]
                log.info("mba_tenant_done", tenant_id=tenant_id, **result)
        except Exception as exc:
            log.error("mba_tenant_failed", tenant_id=tenant_id, error=str(exc))

    log.info("mba_run_complete", tenants=len(tenant_ids), total_upserted=total_upserted)
