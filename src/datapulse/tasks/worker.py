"""Arq worker — executes long-running SQL queries off the API process.

Start with:
    arq datapulse.tasks.worker.WorkerSettings
"""

from __future__ import annotations

import json
import time
from typing import Any

import redis.asyncio as redis_async
from arq.connections import RedisSettings
from sqlalchemy import text

from datapulse.config import get_settings
from datapulse.core.db_session import open_tenant_session  # patchable in tests
from datapulse.core.serializers import serialise_value as _serialise
from datapulse.logging import get_logger

log = get_logger(__name__)


def _job_state_url() -> str:
    """Redis URL for db 2 (job state) — separate from queue (db 1) and cache (db 0)."""
    settings = get_settings()
    base = settings.redis_url
    if not base:
        return "redis://localhost:6379/2"
    parts = base.rsplit("/", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]}/2"
    return f"{base.rstrip('/')}/2"


def _open_job_client() -> redis_async.Redis:
    """Async Redis client for job state writes (db 2). Patchable in tests."""
    return redis_async.from_url(_job_state_url(), decode_responses=True, socket_timeout=2)


def _redis_settings() -> RedisSettings:
    """Build Arq RedisSettings pointing to db 1 (queue)."""
    settings = get_settings()
    base = settings.redis_url
    if not base:
        return RedisSettings()
    parts = base.rsplit("/", 1)
    queue_url = (
        f"{parts[0]}/1" if len(parts) == 2 and parts[1].isdigit() else f"{base.rstrip('/')}/1"
    )
    return RedisSettings.from_dsn(queue_url)


async def _set_job(client: redis_async.Redis, job_id: str, data: dict[str, Any]) -> None:
    ttl = max(1, get_settings().query_job_ttl)
    await client.setex(f"datapulse:query:{job_id}", ttl, json.dumps(data))


async def run_query_task(
    ctx: dict[str, Any],
    *,
    job_id: str,
    sql: str,
    params: dict[str, Any] | None,
    tenant_id: str,
    row_limit: int,
) -> None:
    """Arq task: execute a SQL query and persist the result in Redis."""
    client = _open_job_client()
    await _set_job(client, job_id, {"status": "running", "submitted_at": time.time()})

    start = time.perf_counter()
    settings = get_settings()
    timeout_s = max(1, settings.query_execution_timeout)
    cap = min(row_limit, max(1, settings.query_row_limit))

    session = open_tenant_session(tenant_id, timeout_s=timeout_s)
    try:
        result = session.execute(text(sql), params or {})
        columns = list(result.keys())
        rows: list[list[Any]] = []
        truncated = False
        for i, row in enumerate(result):
            if i >= cap:
                truncated = True
                break
            rows.append([_serialise(v) for v in row])

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        await _set_job(
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
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        msg = str(exc)
        if "canceling statement due to statement timeout" in msg:
            msg = "Query timed out"
        await _set_job(
            client,
            job_id,
            {"status": "failed", "error": msg[:500], "duration_ms": duration_ms},
        )
    finally:
        session.close()
        await client.close()


async def _on_startup(ctx: dict[str, Any]) -> None:
    log.info("arq_worker_starting", queue=get_settings().arq_queue_name)


async def _on_shutdown(ctx: dict[str, Any]) -> None:
    log.info("arq_worker_stopping")


class WorkerSettings:
    functions = [run_query_task]
    redis_settings = _redis_settings()
    queue_name = get_settings().arq_queue_name
    max_jobs = get_settings().arq_max_jobs
    job_timeout = get_settings().arq_job_timeout
    keep_result = get_settings().query_job_ttl
    on_startup = _on_startup
    on_shutdown = _on_shutdown
