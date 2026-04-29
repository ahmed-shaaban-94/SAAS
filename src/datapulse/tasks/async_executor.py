"""Async query executor — thin shim over Arq + Redis job state.

Public API (preserved for backward compatibility):
- submit_query (async) — enqueues a job via Arq, returns job_id or None
- get_job_result (sync) — reads job state from Redis db 2
- QueryCapacityExceededError — kept for callers' except clauses

Concurrency control has moved from in-process slot accounting to Arq's
``WorkerSettings.max_jobs``.  The slot reservation helpers are removed.
"""

from __future__ import annotations

import contextlib
import json
import time
import uuid

import redis

from datapulse.config import get_settings
from datapulse.logging import get_logger
from datapulse.tasks.queue import get_arq_pool

log = get_logger(__name__)


class QueryCapacityExceededError(RuntimeError):
    """Raised when the Arq queue is saturated or unavailable."""


def _job_ttl() -> int:
    """Job TTL in Redis — reads from settings."""
    return get_settings().query_job_ttl


def _query_timeout() -> int:
    """Hard timeout for query execution — reads from settings."""
    return get_settings().query_execution_timeout


def _effective_row_limit(row_limit: int) -> int:
    """Clamp client row limits to the configured safety ceiling."""
    return min(row_limit, max(1, get_settings().query_row_limit))


def _get_job_client():
    """Return a sync Redis client for job state (db 2).

    Used by health.py ping checks and by submit_query / get_job_result.
    Returns None when Redis is unconfigured.
    """
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        base = settings.redis_url
        parts = base.rsplit("/", 1)
        url = f"{parts[0]}/2" if len(parts) == 2 and parts[1].isdigit() else f"{base.rstrip('/')}/2"
        return redis.from_url(url, decode_responses=True, socket_timeout=2)
    except Exception as exc:  # noqa: BLE001
        log.error("job_redis_connect_error", error=str(exc))
        return None


def _set_job(client, job_id: str, data: dict) -> None:
    """Write job state to Redis with TTL."""
    client.setex(f"datapulse:query:{job_id}", _job_ttl(), json.dumps(data))


async def _get_arq_pool():
    """Indirection layer kept for monkeypatching in tests."""
    return await get_arq_pool()


async def submit_query(
    sql: str,
    tenant_id: str = "1",
    row_limit: int = 10_000,
    params: dict | None = None,
) -> str | None:
    """Enqueue a query for background execution via Arq.

    Returns a ``job_id`` (UUID string) on success, or ``None`` when Redis
    is unavailable.  Raises ``QueryCapacityExceededError`` if the Arq pool
    rejects the job (e.g. queue full / connection lost).
    """
    client = _get_job_client()
    if client is None:
        return None

    pool = await _get_arq_pool()
    if pool is None:
        return None

    job_id = str(uuid.uuid4())
    effective_row_limit = _effective_row_limit(row_limit)
    _set_job(client, job_id, {"status": "pending", "submitted_at": time.time()})

    try:
        await pool.enqueue_job(
            "run_query_task",
            job_id=job_id,
            sql=sql,
            params=params,
            tenant_id=tenant_id,
            row_limit=effective_row_limit,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("arq_enqueue_failed", error=str(exc), job_id=job_id)
        with contextlib.suppress(Exception):
            _set_job(client, job_id, {"status": "failed", "error": "Failed to enqueue"})
        raise QueryCapacityExceededError("Queue unavailable") from exc

    log.info("query_submitted", job_id=job_id, tenant_id=tenant_id)
    return job_id


def get_job_result(job_id: str) -> dict | None:
    """Get the current state of a query job from Redis (db 2).

    Includes a staleness check: if a job has been "running" for longer
    than ``_query_timeout() + 60`` seconds, return a synthetic "failed"
    result so clients don't poll forever.
    """
    client = _get_job_client()
    if client is None:
        return None
    try:
        raw = client.get(f"datapulse:query:{job_id}")
        if raw is None:
            return None
        data = json.loads(raw)

        # Staleness detection: if running too long, mark as failed
        if data.get("status") == "running":
            submitted_at = data.get("submitted_at")
            if submitted_at is not None:
                elapsed = time.time() - submitted_at
                stale_threshold = _query_timeout() + 60
                if elapsed > stale_threshold:
                    log.warning(
                        "stale_job_detected",
                        job_id=job_id,
                        elapsed_seconds=round(elapsed, 1),
                    )
                    failed_data = {
                        "status": "failed",
                        "error": (
                            f"Job appears stale — running for {round(elapsed)}s"
                            f" (threshold {stale_threshold}s). The worker may"
                            " have crashed."
                        ),
                    }
                    with contextlib.suppress(Exception):
                        _set_job(client, job_id, failed_data)
                    return failed_data

        return data
    except Exception as exc:  # noqa: BLE001
        log.error("job_get_error", job_id=job_id, error=str(exc))
        return None
