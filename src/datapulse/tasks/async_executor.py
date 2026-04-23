"""Lightweight async query executor using Redis for job state.

Replaces Celery for async query execution. Runs queries in background
threads via asyncio.to_thread and stores results in Redis (same instance
used for caching, but in db 2 to avoid key collisions).

Design:
- submit_query() → creates a job record in Redis, spawns a background task
- get_job_result() → reads the job record from Redis
- _run_query() → the actual query execution (runs in a thread)
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid

import redis
from sqlalchemy import text

from datapulse.config import get_settings
from datapulse.core.serializers import serialise_value as _serialise
from datapulse.logging import get_logger

log = get_logger(__name__)

_QUERY_SLOT_LOCK = threading.Lock()
_QUERY_SLOTS_IN_USE = 0
_QUERY_SLOTS_BY_TENANT: dict[str, int] = {}


class QueryCapacityExceededError(RuntimeError):
    """Raised when the async query executor is already saturated."""


def _job_ttl() -> int:
    """Job TTL in Redis — reads from settings."""
    return get_settings().query_job_ttl


def _query_timeout() -> int:
    """Hard timeout for query execution — reads from settings."""
    return get_settings().query_execution_timeout


def _effective_row_limit(row_limit: int) -> int:
    """Clamp client row limits to the configured safety ceiling."""
    configured_limit = max(1, get_settings().query_row_limit)
    return min(row_limit, configured_limit)


def _max_concurrent_jobs() -> int:
    return max(1, get_settings().query_max_concurrent_jobs)


def _max_concurrent_jobs_per_tenant() -> int:
    settings = get_settings()
    return max(
        1,
        min(settings.query_max_concurrent_jobs_per_tenant, _max_concurrent_jobs()),
    )


def _reserve_query_slot(tenant_id: str) -> None:
    """Reserve a local worker slot before scheduling a heavy async query."""
    global _QUERY_SLOTS_IN_USE

    with _QUERY_SLOT_LOCK:
        tenant_slots = _QUERY_SLOTS_BY_TENANT.get(tenant_id, 0)
        if _max_concurrent_jobs() <= _QUERY_SLOTS_IN_USE:
            raise QueryCapacityExceededError("Too many async queries are already running.")
        if tenant_slots >= _max_concurrent_jobs_per_tenant():
            raise QueryCapacityExceededError("Tenant async query capacity reached. Retry shortly.")

        _QUERY_SLOTS_IN_USE += 1
        _QUERY_SLOTS_BY_TENANT[tenant_id] = tenant_slots + 1


def _release_query_slot(tenant_id: str) -> None:
    """Release a previously reserved local worker slot."""
    global _QUERY_SLOTS_IN_USE

    with _QUERY_SLOT_LOCK:
        tenant_slots = _QUERY_SLOTS_BY_TENANT.get(tenant_id, 0)
        if tenant_slots <= 1:
            _QUERY_SLOTS_BY_TENANT.pop(tenant_id, None)
        elif tenant_slots > 1:
            _QUERY_SLOTS_BY_TENANT[tenant_id] = tenant_slots - 1

        if _QUERY_SLOTS_IN_USE > 0:
            _QUERY_SLOTS_IN_USE -= 1


def _get_job_client():
    """Return a Redis client for job state (db 2)."""
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        base = settings.redis_url
        parts = base.rsplit("/", 1)
        url = f"{parts[0]}/2" if len(parts) == 2 and parts[1].isdigit() else f"{base.rstrip('/')}/2"

        return redis.from_url(url, decode_responses=True, socket_timeout=2)
    except Exception as exc:
        log.error("job_redis_connect_error", error=str(exc))
        return None


def _set_job(client, job_id: str, data: dict) -> None:
    """Write job state to Redis with TTL."""
    client.setex(f"datapulse:query:{job_id}", _job_ttl(), json.dumps(data))


def _run_query_sync(
    job_id: str,
    sql: str,
    params: dict | None,
    tenant_id: str,
    row_limit: int,
) -> None:
    """Execute a SQL query and store the result in Redis.

    This function runs in a background thread. It manages its own
    DB session and Redis connection.
    """
    client = _get_job_client()
    if client is None:
        log.error("job_no_redis", job_id=job_id)
        return

    # Mark as running with submission timestamp for staleness detection
    _set_job(client, job_id, {"status": "running", "submitted_at": time.time()})

    start = time.perf_counter()
    from datapulse.core.db_session import open_tenant_session

    session = open_tenant_session(tenant_id, timeout_s=_query_timeout())
    try:
        result = session.execute(text(sql), params or {})
        columns = list(result.keys())
        rows = []
        truncated = False

        for i, row in enumerate(result):
            if i >= _effective_row_limit(row_limit):
                truncated = True
                break
            rows.append([_serialise(v) for v in row])

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        log.info(
            "query_executed",
            job_id=job_id,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=duration_ms,
        )

        _set_job(
            client,
            job_id,
            {
                "status": "complete",
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "duration_ms": duration_ms,
            },
        )
    except Exception as exc:
        session.rollback()
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        error_msg = str(exc)
        if "canceling statement due to statement timeout" in error_msg:
            error_msg = "Query timed out after 270 seconds"

        log.error("query_failed", job_id=job_id, error=error_msg, duration_ms=duration_ms)
        try:
            _set_job(
                client,
                job_id,
                {
                    "status": "failed",
                    "error": error_msg[:500],
                    "duration_ms": duration_ms,
                },
            )
        except Exception as redis_exc:
            log.error(
                "job_redis_write_error",
                job_id=job_id,
                error=str(redis_exc),
            )
    finally:
        session.close()


def _run_query_job_sync(
    job_id: str,
    sql: str,
    params: dict | None,
    tenant_id: str,
    row_limit: int,
) -> None:
    """Run a query job and always release its worker slot afterward."""
    try:
        _run_query_sync(job_id, sql, params, tenant_id, row_limit)
    finally:
        _release_query_slot(tenant_id)


async def submit_query(
    sql: str,
    tenant_id: str = "1",
    row_limit: int = 10_000,
    params: dict | None = None,
) -> str | None:
    """Submit a query for background execution. Returns job_id or None."""
    client = _get_job_client()
    if client is None:
        return None

    _reserve_query_slot(tenant_id)

    job_id = str(uuid.uuid4())
    effective_row_limit = _effective_row_limit(row_limit)

    try:
        _set_job(client, job_id, {"status": "pending"})

        # Fire and forget — bounded by explicit capacity reservation above.
        asyncio.get_event_loop().run_in_executor(
            None,
            _run_query_job_sync,
            job_id,
            sql,
            params,
            tenant_id,
            effective_row_limit,
        )
    except BaseException:
        _release_query_slot(tenant_id)
        raise

    log.info("query_submitted", job_id=job_id, tenant_id=tenant_id)
    return job_id


def get_job_result(job_id: str) -> dict | None:
    """Get the current state of a query job from Redis.

    Includes a staleness check: if a job has been "running" for longer
    than ``_QUERY_TIMEOUT + 60`` seconds, return a synthetic "failed"
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
                    # Best-effort update in Redis so subsequent polls
                    # also see the failed state.
                    import contextlib

                    with contextlib.suppress(Exception):
                        _set_job(client, job_id, failed_data)
                    return failed_data

        return data
    except Exception as exc:
        log.error("job_get_error", job_id=job_id, error=str(exc))
        return None
