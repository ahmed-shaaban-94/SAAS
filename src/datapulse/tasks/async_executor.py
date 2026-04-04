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
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from datapulse.config import get_settings
from datapulse.core.db import get_session_factory
from datapulse.logging import get_logger

log = get_logger(__name__)

# Job TTL in Redis (1 hour)
_JOB_TTL = 3600
# Hard timeout for query execution (5 minutes)
_QUERY_TIMEOUT = 300


def _get_job_client():
    """Return a Redis client for job state (db 2)."""
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        import redis

        base = settings.redis_url
        parts = base.rsplit("/", 1)
        url = f"{parts[0]}/2" if len(parts) == 2 and parts[1].isdigit() else f"{base.rstrip('/')}/2"

        return redis.from_url(url, decode_responses=True, socket_timeout=2)
    except Exception as exc:
        log.error("job_redis_connect_error", error=str(exc))
        return None


def _serialise(value: Any) -> str | int | float | bool | None:
    """Convert a DB value to a JSON-safe primitive."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


def _set_job(client, job_id: str, data: dict) -> None:
    """Write job state to Redis with TTL."""
    client.setex(f"datapulse:query:{job_id}", _JOB_TTL, json.dumps(data))


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

    # Mark as running
    _set_job(client, job_id, {"status": "running"})

    start = time.perf_counter()
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        session.execute(text("SET LOCAL statement_timeout = '270s'"))

        result = session.execute(text(sql), params or {})
        columns = list(result.keys())
        rows = []
        truncated = False

        for i, row in enumerate(result):
            if i >= row_limit:
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
        _set_job(
            client,
            job_id,
            {
                "status": "failed",
                "error": error_msg[:500],
                "duration_ms": duration_ms,
            },
        )
    finally:
        session.close()


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

    job_id = str(uuid.uuid4())
    _set_job(client, job_id, {"status": "pending"})

    # Fire and forget — run in background thread
    asyncio.get_event_loop().run_in_executor(
        None,
        _run_query_sync,
        job_id,
        sql,
        params,
        tenant_id,
        row_limit,
    )

    log.info("query_submitted", job_id=job_id, tenant_id=tenant_id)
    return job_id


def get_job_result(job_id: str) -> dict | None:
    """Get the current state of a query job from Redis."""
    client = _get_job_client()
    if client is None:
        return None
    try:
        raw = client.get(f"datapulse:query:{job_id}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        log.error("job_get_error", job_id=job_id, error=str(exc))
        return None
