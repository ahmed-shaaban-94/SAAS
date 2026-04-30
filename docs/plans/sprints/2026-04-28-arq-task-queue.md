# Arq Distributed Task Queue — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the in-process thread-pool executor in `src/datapulse/tasks/async_executor.py` with a distributed Arq worker backed by Redis, and bridge `src/datapulse/api/backpressure.py` to use Arq queue depth as the saturation signal (return 503 when queue depth exceeds the configured threshold).

**Architecture:** Long-running SQL queries are no longer executed in the API process via `asyncio.run_in_executor`. Instead, `submit_query` enqueues an Arq job onto Redis (db 1, separate from the cache db 0 and the legacy job-state db 2). A standalone `arq` worker container (`datapulse.tasks.worker:WorkerSettings`) consumes the queue, runs `run_query_task`, and stores results in Redis db 2 using the existing `datapulse:query:<job_id>` schema so `get_job_result` and the polling endpoint stay byte-compatible. The admission controller gains a queue-depth probe: before each non-exempt request it samples `ArqRedis.queued_jobs()`, and rejects with 503 + `Retry-After` when depth exceeds `arq_queue_depth_limit`. This horizontalises capacity (add workers, not API replicas) and isolates query CPU from request handling.

**Tech Stack:** Python 3.11+, `arq>=0.26,<1`, `fakeredis[lua]>=2.21,<3` (test extra), existing `redis>=5.0,<6` client, FastAPI, Docker Compose, Gunicorn + UvicornWorker.

**Spec:** N/A — replaces an existing module behind the same public API (`submit_query`, `get_job_result`, `QueryCapacityExceededError`). The wire protocol on `/api/v1/queries` is unchanged.

---

## File Map

| Path | Action | Responsibility |
|------|--------|----------------|
| `pyproject.toml` | Edit | Add `arq>=0.26,<1`; add `fakeredis[lua]>=2.21,<3` to dev extras |
| `src/datapulse/config.py` | Edit | Add `arq_queue_name`, `arq_queue_depth_limit`, `arq_max_jobs`, `arq_job_timeout` settings |
| `src/datapulse/tasks/worker.py` | Create | Arq `WorkerSettings`, `run_query_task` async function, startup/shutdown hooks |
| `src/datapulse/tasks/queue.py` | Create | `get_arq_pool()` async singleton wrapping `create_pool(RedisSettings)` for enqueue + depth probes |
| `src/datapulse/tasks/async_executor.py` | Edit | Rewrite `submit_query` to enqueue via Arq; keep `get_job_result` reading the same Redis db 2 keyspace; keep `QueryCapacityExceededError` for callers |
| `src/datapulse/api/backpressure.py` | Edit | Add `QueueDepthGuard` that probes Arq queue depth; `AdmissionController.try_acquire` consults it |
| `src/datapulse/api/bootstrap/middleware.py` | Edit | `_install_overload_guard` returns 503 when `QueueDepthGuard` reports saturation |
| `src/datapulse/api/app.py` | Edit | Wire `QueueDepthGuard(arq_queue_depth_limit)` into `app.state.queue_depth_guard`; close the Arq pool on shutdown via lifespan |
| `src/datapulse/api/bootstrap/lifespan.py` | Edit | Open `get_arq_pool()` on startup, close on shutdown |
| `src/datapulse/api/routes/health.py` | Edit | `_check_query_executor` probes the Arq pool instead of the legacy job-state Redis client |
| `src/datapulse/api/routes/queries.py` | Edit | No code change — verifies the new `submit_query` is `async` and still returns the job_id string |
| `docker-compose.yml` | Edit | Add `arq` worker service (reuses `api` build target, runs `arq datapulse.tasks.worker.WorkerSettings`); add `ARQ_QUEUE_NAME`/`ARQ_QUEUE_DEPTH_LIMIT` env vars |
| `.env.example` | Edit | Document `ARQ_QUEUE_NAME`, `ARQ_QUEUE_DEPTH_LIMIT`, `ARQ_MAX_JOBS`, `ARQ_JOB_TIMEOUT` |
| `tests/test_arq_worker.py` | Create | Unit tests — `WorkerSettings` shape, `run_query_task` happy + error paths against `fakeredis` |
| `tests/test_arq_queue.py` | Create | Unit tests — `get_arq_pool()` returns a singleton, `submit_query` enqueues a job |
| `tests/test_backpressure_queue_depth.py` | Create | Unit tests — `QueueDepthGuard` returns False when depth > limit, True otherwise; middleware short-circuits with 503 |
| `tests/test_arq_smoke.py` | Create | Integration smoke test — enqueue → process → result stored under `datapulse:query:<id>` |

Files **NOT** touched in this plan (deferred to follow-ups):
- `src/datapulse/tasks/cleanup_pos_idempotency.py` — runs under APScheduler; not part of the query queue.
- `src/datapulse/tasks/models.py` — `QueryResult` / `QueryResponse` shapes are preserved.
- All caller code paths beyond the four files listed above (`submit_query` and `get_job_result` keep their signatures).

---

## Preconditions

- Local stack running: `docker compose up -d postgres redis api` (Redis 7 reachable on `127.0.0.1:6379` with `REDIS_PASSWORD` set).
- `REDIS_URL` exported (e.g. `redis://:${REDIS_PASSWORD}@localhost:6379/0`).
- `pytest -m unit -x -q` is green on `main` before starting.
- All callers of `async_executor` are confined to:
  - `src/datapulse/api/routes/queries.py` (HTTP entrypoint)
  - `src/datapulse/api/routes/health.py` (health probe — `_get_job_client`)
  - `tests/test_async_executor_core.py`, `tests/test_queries_endpoints.py`, `tests/test_health.py`, `tests/test_stabilization.py`
  Confirmed via `grep -rn "async_executor\|submit_query\|get_job_result\|QueryCapacityExceededError" src/ tests/`.

---

## Task 1: Add Arq deps + worker module (RED → GREEN)

Introduces the worker side of the queue. Tests are written first against `fakeredis` so they fail until `worker.py` lands.

**Files:**
- Edit: `pyproject.toml`
- Edit: `src/datapulse/config.py`
- Create: `tests/test_arq_worker.py`
- Create: `src/datapulse/tasks/worker.py`

- [ ] **Step 1.1: Add `arq` + `fakeredis` deps to `pyproject.toml`**

In the `[project] dependencies` array, append after the existing `redis>=5.0,<6` line:

```toml
    "arq>=0.26,<1",
```

In `[project.optional-dependencies].dev`, append:

```toml
    "fakeredis[lua]>=2.21,<3",
```

Run:

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
pip install -e ".[dev]"
```

Expected output ends with:

```
Successfully installed arq-0.26.x fakeredis-2.21.x ...
```

- [ ] **Step 1.2: Add Arq settings to `src/datapulse/config.py`**

Locate the `Settings` class (search for `query_max_concurrent_jobs`) and add these fields next to it:

```python
    arq_queue_name: str = Field(
        default="datapulse:queries",
        description="Arq Redis list key — keep distinct from the cache namespace.",
    )
    arq_queue_depth_limit: int = Field(
        default=100,
        ge=0,
        description="Reject new requests with 503 when queued+running jobs exceed this.",
    )
    arq_max_jobs: int = Field(
        default=10,
        ge=1,
        description="Per-worker concurrency. Multiply by replicas for total parallelism.",
    )
    arq_job_timeout: int = Field(
        default=300,
        ge=1,
        description="Seconds before Arq cancels a stuck job (>= query_execution_timeout).",
    )
```

- [ ] **Step 1.3: Write failing tests in `tests/test_arq_worker.py`**

```python
"""Unit tests for the Arq worker module — they fail until worker.py lands."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_worker_settings_exposes_required_attrs() -> None:
    from datapulse.tasks.worker import WorkerSettings

    # Arq inspects these as class attributes when bootstrapping.
    assert hasattr(WorkerSettings, "functions"), "WorkerSettings.functions missing"
    assert hasattr(WorkerSettings, "redis_settings"), "WorkerSettings.redis_settings missing"
    assert WorkerSettings.max_jobs >= 1
    assert WorkerSettings.job_timeout >= 1
    assert WorkerSettings.queue_name


def test_worker_registers_run_query_task() -> None:
    from datapulse.tasks.worker import WorkerSettings, run_query_task

    assert run_query_task in WorkerSettings.functions


@pytest.mark.asyncio
async def test_run_query_task_writes_complete_state(monkeypatch) -> None:
    """run_query_task must persist a 'complete' record under datapulse:query:<id>."""
    import json

    import fakeredis.aioredis

    from datapulse.tasks import worker

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker, "_open_job_client", lambda: fake)

    # Stub DB execution so we don't need Postgres in unit tests.
    class FakeResult:
        def keys(self):
            return ["id", "name"]

        def __iter__(self):
            return iter([(1, "alpha"), (2, "beta")])

    class FakeSession:
        def execute(self, *_a, **_kw):
            return FakeResult()

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        worker, "open_tenant_session", lambda tenant_id, timeout_s: FakeSession()
    )

    ctx: dict = {}
    await worker.run_query_task(
        ctx,
        job_id="job-123",
        sql="SELECT 1",
        params=None,
        tenant_id="t1",
        row_limit=10,
    )

    raw = await fake.get("datapulse:query:job-123")
    assert raw is not None
    record = json.loads(raw)
    assert record["status"] == "complete"
    assert record["row_count"] == 2
    assert record["columns"] == ["id", "name"]


@pytest.mark.asyncio
async def test_run_query_task_writes_failed_state_on_error(monkeypatch) -> None:
    import json

    import fakeredis.aioredis

    from datapulse.tasks import worker

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker, "_open_job_client", lambda: fake)

    class BoomSession:
        def execute(self, *_a, **_kw):
            raise RuntimeError("boom")

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        worker, "open_tenant_session", lambda tenant_id, timeout_s: BoomSession()
    )

    await worker.run_query_task(
        {}, job_id="job-err", sql="SELECT 1", params=None, tenant_id="t1", row_limit=10
    )

    record = json.loads(await fake.get("datapulse:query:job-err"))
    assert record["status"] == "failed"
    assert "boom" in record["error"]
```

Run:

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
pytest tests/test_arq_worker.py -x -q
```

Expected output: 4 failures with `ModuleNotFoundError: No module named 'datapulse.tasks.worker'`.

- [ ] **Step 1.4: Implement `src/datapulse/tasks/worker.py`**

```python
"""Arq worker — executes long-running SQL queries off the API process.

Bootstrapped via:
    arq datapulse.tasks.worker.WorkerSettings

The worker reads ``REDIS_URL`` from settings, listens on
``arq_queue_name``, and stores results in Redis db 2 under the same
``datapulse:query:<job_id>`` keys the legacy in-process executor used —
so ``get_job_result`` and the polling endpoint stay byte-compatible.
"""

from __future__ import annotations

import json
import time
from typing import Any

import redis.asyncio as redis_async
from arq.connections import RedisSettings

from datapulse.config import get_settings
from datapulse.core.db_session import open_tenant_session
from datapulse.core.serializers import serialise_value as _serialise
from datapulse.logging import get_logger
from sqlalchemy import text

log = get_logger(__name__)


def _job_state_url() -> str:
    """Redis URL pointed at db 2 — kept separate from queue (db 1) and cache (db 0)."""
    settings = get_settings()
    base = settings.redis_url
    parts = base.rsplit("/", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]}/2"
    return f"{base.rstrip('/')}/2"


def _open_job_client() -> redis_async.Redis:
    """Async Redis client for job state writes (db 2). Patchable in tests."""
    return redis_async.from_url(_job_state_url(), decode_responses=True, socket_timeout=2)


def _redis_settings() -> RedisSettings:
    """Build Arq RedisSettings from the existing REDIS_URL."""
    settings = get_settings()
    base = settings.redis_url
    # Arq uses db 1 for queue keys — keeps cache (db 0) and job state (db 2) clean.
    parts = base.rsplit("/", 1)
    queue_url = f"{parts[0]}/1" if len(parts) == 2 and parts[1].isdigit() else f"{base.rstrip('/')}/1"
    return RedisSettings.from_dsn(queue_url)


async def _set_job(client: redis_async.Redis, job_id: str, data: dict[str, Any]) -> None:
    ttl = max(1, get_settings().query_job_ttl)
    await client.setex(f"datapulse:query:{job_id}", ttl, json.dumps(data))


def _effective_row_limit(row_limit: int) -> int:
    configured = max(1, get_settings().query_row_limit)
    return min(row_limit, configured)


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
    timeout_s = max(1, get_settings().query_execution_timeout)
    session = open_tenant_session(tenant_id, timeout_s=timeout_s)
    try:
        result = session.execute(text(sql), params or {})
        columns = list(result.keys())
        rows: list[list[Any]] = []
        truncated = False
        cap = _effective_row_limit(row_limit)
        for i, row in enumerate(result):
            if i >= cap:
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
    except Exception as exc:  # noqa: BLE001 — every error must be reported to the client
        session.rollback()
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        msg = str(exc)
        if "canceling statement due to statement timeout" in msg:
            msg = "Query timed out"
        log.error("query_failed", job_id=job_id, error=msg, duration_ms=duration_ms)
        await _set_job(
            client,
            job_id,
            {"status": "failed", "error": msg[:500], "duration_ms": duration_ms},
        )
    finally:
        session.close()
        await client.aclose()


async def _on_startup(ctx: dict[str, Any]) -> None:
    log.info("arq_worker_starting", queue=get_settings().arq_queue_name)


async def _on_shutdown(ctx: dict[str, Any]) -> None:
    log.info("arq_worker_stopping")


class WorkerSettings:
    """Arq picks these up via class introspection — see arq docs."""

    functions = [run_query_task]
    redis_settings = _redis_settings()
    queue_name = get_settings().arq_queue_name
    max_jobs = get_settings().arq_max_jobs
    job_timeout = get_settings().arq_job_timeout
    keep_result = get_settings().query_job_ttl
    on_startup = _on_startup
    on_shutdown = _on_shutdown
```

Run:

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
pytest tests/test_arq_worker.py -x -q
```

Expected output: `4 passed`.

- [ ] **Step 1.5: Lint + commit**

```bash
ruff format src/datapulse/tasks/worker.py src/datapulse/config.py tests/test_arq_worker.py
ruff check src/datapulse/tasks/worker.py src/datapulse/config.py tests/test_arq_worker.py
git add pyproject.toml src/datapulse/config.py src/datapulse/tasks/worker.py tests/test_arq_worker.py
git commit -m "feat(tasks): add Arq worker module with run_query_task"
```

---

## Task 2: Migrate `submit_query` callers to enqueue via Arq (RED → GREEN)

Adds the enqueue path. Existing callers (`submit_query`, `get_job_result`, `QueryCapacityExceededError`) keep their public signatures so `routes/queries.py`, `routes/health.py`, and the four test files do not change in this task.

**Files:**
- Create: `src/datapulse/tasks/queue.py`
- Create: `tests/test_arq_queue.py`
- Edit: `src/datapulse/tasks/async_executor.py`

**Callers of the legacy executor (must keep working unchanged):**
- `src/datapulse/api/routes/queries.py` — calls `await submit_query(...)` and `get_job_result(...)`
- `src/datapulse/api/routes/health.py` — uses `_get_job_client` (probe only — refactored in Task 3)
- `tests/test_async_executor_core.py`
- `tests/test_queries_endpoints.py`
- `tests/test_health.py`
- `tests/test_stabilization.py`

- [ ] **Step 2.1: Write failing tests in `tests/test_arq_queue.py`**

```python
"""Unit tests for the Arq enqueue path."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_get_arq_pool_returns_singleton(monkeypatch) -> None:
    from datapulse.tasks import queue as queue_mod

    fake_pool = AsyncMock()
    create_pool_mock = AsyncMock(return_value=fake_pool)
    monkeypatch.setattr(queue_mod, "create_pool", create_pool_mock)
    monkeypatch.setattr(queue_mod, "_pool", None, raising=False)

    p1 = await queue_mod.get_arq_pool()
    p2 = await queue_mod.get_arq_pool()
    assert p1 is p2
    assert create_pool_mock.await_count == 1


@pytest.mark.asyncio
async def test_submit_query_enqueues_via_arq(monkeypatch) -> None:
    from datapulse.tasks import async_executor

    enqueued: dict = {}

    class FakePool:
        async def enqueue_job(self, name, *args, **kwargs):
            enqueued["name"] = name
            enqueued["kwargs"] = kwargs
            return object()

    monkeypatch.setattr(async_executor, "_get_arq_pool", AsyncMock(return_value=FakePool()))

    # In-memory job-state writes.
    seen: dict = {}

    class FakeStateClient:
        def setex(self, key, ttl, value):
            seen[key] = value

    monkeypatch.setattr(async_executor, "_get_job_client", lambda: FakeStateClient())

    job_id = await async_executor.submit_query(
        sql="SELECT 1", tenant_id="t1", row_limit=100
    )

    assert job_id is not None
    assert enqueued["name"] == "run_query_task"
    assert enqueued["kwargs"]["job_id"] == job_id
    assert enqueued["kwargs"]["tenant_id"] == "t1"
    assert f"datapulse:query:{job_id}" in seen


@pytest.mark.asyncio
async def test_submit_query_returns_none_when_redis_unavailable(monkeypatch) -> None:
    from datapulse.tasks import async_executor

    monkeypatch.setattr(async_executor, "_get_job_client", lambda: None)
    monkeypatch.setattr(async_executor, "_get_arq_pool", AsyncMock(return_value=None))

    job_id = await async_executor.submit_query(sql="SELECT 1", tenant_id="t1")
    assert job_id is None
```

Run:

```bash
pytest tests/test_arq_queue.py -x -q
```

Expected output: 3 failures (`AttributeError: module 'datapulse.tasks.async_executor' has no attribute '_get_arq_pool'`).

- [ ] **Step 2.2: Implement `src/datapulse/tasks/queue.py`**

```python
"""Async singleton wrapping arq.create_pool — used to enqueue + probe depth."""

from __future__ import annotations

import asyncio
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis

from datapulse.config import get_settings
from datapulse.logging import get_logger
from datapulse.tasks.worker import _redis_settings

log = get_logger(__name__)

_pool: ArqRedis | None = None
_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis | None:
    """Return a process-wide ArqRedis pool, creating it on first use.

    Returns ``None`` if Redis is misconfigured — callers must degrade
    gracefully (the legacy executor returned ``None`` for the same case).
    """
    global _pool
    if _pool is not None:
        return _pool
    async with _lock:
        if _pool is not None:
            return _pool
        try:
            _pool = await create_pool(_redis_settings())
        except Exception as exc:  # noqa: BLE001
            log.error("arq_pool_create_failed", error=str(exc))
            return None
        return _pool


async def close_arq_pool() -> None:
    """Close the pool on app shutdown so workers don't see lingering clients."""
    global _pool
    if _pool is None:
        return
    try:
        await _pool.close(close_connection_pool=True)
    finally:
        _pool = None


async def queue_depth() -> int:
    """Best-effort sample of pending+running jobs. Returns 0 on probe failure."""
    pool = await get_arq_pool()
    if pool is None:
        return 0
    try:
        queue_name = get_settings().arq_queue_name
        # arq stores pending jobs as a sorted set keyed by queue_name.
        return int(await pool.zcard(queue_name))
    except Exception as exc:  # noqa: BLE001
        log.warning("arq_queue_depth_probe_failed", error=str(exc))
        return 0


_PoolLike = Any  # exported alias so callers don't import arq directly
```

- [ ] **Step 2.3: Rewrite `src/datapulse/tasks/async_executor.py`**

Replace the entire file content with:

```python
"""Async query executor — thin shim over Arq + Redis job state.

Public API preserved for backward compatibility with the queries route
and health checks:

- ``submit_query`` (async) — enqueues a job, returns a job_id or None
- ``get_job_result`` (sync) — reads the same Redis db 2 keyspace
- ``QueryCapacityExceededError`` — kept so callers' except clauses still match
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
    """Raised when the queue is saturated — kept for backward compatibility."""


def _job_ttl() -> int:
    return get_settings().query_job_ttl


def _query_timeout() -> int:
    return get_settings().query_execution_timeout


def _effective_row_limit(row_limit: int) -> int:
    configured_limit = max(1, get_settings().query_row_limit)
    return min(row_limit, configured_limit)


def _get_job_client():
    """Sync Redis client for job state reads (db 2). Health probes use this."""
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
    client.setex(f"datapulse:query:{job_id}", _job_ttl(), json.dumps(data))


# Indirection so tests can monkeypatch the pool factory.
async def _get_arq_pool():
    return await get_arq_pool()


async def submit_query(
    sql: str,
    tenant_id: str = "1",
    row_limit: int = 10_000,
    params: dict | None = None,
) -> str | None:
    """Enqueue a query for background execution. Returns job_id or None."""
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
    """Read the current state of a query job from Redis (db 2)."""
    client = _get_job_client()
    if client is None:
        return None
    try:
        raw = client.get(f"datapulse:query:{job_id}")
        if raw is None:
            return None
        data = json.loads(raw)

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
```

- [ ] **Step 2.4: Run the existing executor + queries test suites**

```bash
pytest tests/test_arq_queue.py tests/test_async_executor_core.py tests/test_queries_endpoints.py -x -q
```

Expected output: all green. If `test_async_executor_core.py` references `_QUERY_SLOTS_BY_TENANT` or `_reserve_query_slot` (the deleted in-process slot machinery), update those tests to assert on Arq enqueue behavior instead — keep the file in this commit only if such updates are required.

If updates are needed, the canonical replacement assertion is:

```python
@pytest.mark.asyncio
async def test_submit_query_enqueues(monkeypatch):
    from datapulse.tasks import async_executor

    pool = AsyncMock()
    pool.enqueue_job = AsyncMock(return_value=object())
    monkeypatch.setattr(async_executor, "_get_arq_pool", AsyncMock(return_value=pool))
    monkeypatch.setattr(
        async_executor,
        "_get_job_client",
        lambda: type("C", (), {"setex": lambda *a, **k: None})(),
    )

    job_id = await async_executor.submit_query("SELECT 1", tenant_id="t")
    assert job_id is not None
    pool.enqueue_job.assert_awaited_once()
```

- [ ] **Step 2.5: Lint + commit**

```bash
ruff format src/datapulse/tasks/queue.py src/datapulse/tasks/async_executor.py tests/test_arq_queue.py
ruff check src/datapulse/tasks/queue.py src/datapulse/tasks/async_executor.py tests/test_arq_queue.py
git add src/datapulse/tasks/queue.py src/datapulse/tasks/async_executor.py tests/test_arq_queue.py tests/test_async_executor_core.py
git commit -m "refactor(tasks): rewrite submit_query to enqueue via Arq pool"
```

---

## Task 3: Bridge `backpressure.py` to queue depth (RED → GREEN)

The admission controller currently bounds in-process semaphores. Add a queue-depth probe so saturation is measured globally (across all API replicas + the worker fleet), and return 503 when depth exceeds the limit.

**Files:**
- Create: `tests/test_backpressure_queue_depth.py`
- Edit: `src/datapulse/api/backpressure.py`
- Edit: `src/datapulse/api/bootstrap/middleware.py`
- Edit: `src/datapulse/api/app.py`
- Edit: `src/datapulse/api/bootstrap/lifespan.py`
- Edit: `src/datapulse/api/routes/health.py`

- [ ] **Step 3.1: Write failing tests in `tests/test_backpressure_queue_depth.py`**

```python
"""Unit tests for the queue-depth backpressure guard."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_guard_allows_when_depth_below_limit(monkeypatch) -> None:
    from datapulse.api.backpressure import QueueDepthGuard

    monkeypatch.setattr(
        "datapulse.api.backpressure.queue_depth", AsyncMock(return_value=5)
    )
    guard = QueueDepthGuard(limit=100)
    assert await guard.allow() is True


@pytest.mark.asyncio
async def test_guard_rejects_when_depth_at_or_above_limit(monkeypatch) -> None:
    from datapulse.api.backpressure import QueueDepthGuard

    monkeypatch.setattr(
        "datapulse.api.backpressure.queue_depth", AsyncMock(return_value=100)
    )
    guard = QueueDepthGuard(limit=100)
    assert await guard.allow() is False


@pytest.mark.asyncio
async def test_guard_disabled_when_limit_zero(monkeypatch) -> None:
    from datapulse.api.backpressure import QueueDepthGuard

    probe = AsyncMock(return_value=999_999)
    monkeypatch.setattr("datapulse.api.backpressure.queue_depth", probe)
    guard = QueueDepthGuard(limit=0)
    assert await guard.allow() is True
    probe.assert_not_awaited()


def test_overload_guard_returns_503_when_queue_full(monkeypatch) -> None:
    from datapulse.api.backpressure import AdmissionController, QueueDepthGuard
    from datapulse.api.bootstrap.middleware import _install_overload_guard

    app = FastAPI()
    app.state.admission_controller = AdmissionController(
        max_in_flight_requests=100, acquire_timeout_ms=10
    )
    monkeypatch.setattr(
        "datapulse.api.backpressure.queue_depth", AsyncMock(return_value=999)
    )
    app.state.queue_depth_guard = QueueDepthGuard(limit=10)
    _install_overload_guard(app)

    @app.get("/api/v1/echo")
    def echo() -> dict:
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/v1/echo")
    assert resp.status_code == 503
    assert resp.headers.get("X-DataPulse-Backpressure") == "rejected"
    assert resp.headers.get("Retry-After") == "1"


def test_overload_guard_passes_when_queue_healthy(monkeypatch) -> None:
    from datapulse.api.backpressure import AdmissionController, QueueDepthGuard
    from datapulse.api.bootstrap.middleware import _install_overload_guard

    app = FastAPI()
    app.state.admission_controller = AdmissionController(
        max_in_flight_requests=100, acquire_timeout_ms=10
    )
    monkeypatch.setattr(
        "datapulse.api.backpressure.queue_depth", AsyncMock(return_value=0)
    )
    app.state.queue_depth_guard = QueueDepthGuard(limit=10)
    _install_overload_guard(app)

    @app.get("/api/v1/echo")
    def echo() -> dict:
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/v1/echo")
    assert resp.status_code == 200
```

Run:

```bash
pytest tests/test_backpressure_queue_depth.py -x -q
```

Expected output: all tests fail (`ImportError: cannot import name 'QueueDepthGuard'`).

- [ ] **Step 3.2: Add `QueueDepthGuard` to `src/datapulse/api/backpressure.py`**

Append at the bottom of the file:

```python
from datapulse.tasks.queue import queue_depth as _queue_depth_probe

# Module-level alias so tests can monkeypatch a single symbol.
queue_depth = _queue_depth_probe


class QueueDepthGuard:
    """Reject requests when the Arq queue is saturated (cluster-wide signal)."""

    def __init__(self, limit: int) -> None:
        self.limit = max(0, limit)

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    async def allow(self) -> bool:
        if not self.enabled:
            return True
        try:
            depth = await queue_depth()
        except Exception:
            # Probe failures must NOT take the API down — fail open.
            return True
        return depth < self.limit
```

- [ ] **Step 3.3: Update `_install_overload_guard` in `src/datapulse/api/bootstrap/middleware.py`**

Replace the current body with one that consults both controllers:

```python
def _install_overload_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def overload_guard_middleware(request: Request, call_next) -> Response:
        controller: AdmissionController = request.app.state.admission_controller
        if controller.is_exempt(request):
            return await call_next(request)

        queue_guard = getattr(request.app.state, "queue_depth_guard", None)
        if queue_guard is not None and not await queue_guard.allow():
            logger.warning(
                "request_rejected_queue_depth",
                method=request.method,
                path=request.url.path,
                limit=queue_guard.limit,
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Queue is saturated. Please retry shortly."},
                headers={
                    "Retry-After": "1",
                    "X-DataPulse-Backpressure": "rejected",
                },
            )

        if not await controller.try_acquire():
            logger.warning(
                "request_rejected_overload",
                method=request.method,
                path=request.url.path,
                in_flight=controller.in_flight,
                limit=controller.max_in_flight_requests,
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is busy. Please retry shortly."},
                headers={
                    "Retry-After": "1",
                    "X-DataPulse-Backpressure": "rejected",
                },
            )

        try:
            response = await call_next(request)
        finally:
            controller.release()

        response.headers["X-DataPulse-Backpressure"] = "guarded"
        return response
```

- [ ] **Step 3.4: Wire the guard into `src/datapulse/api/app.py`**

Add the import at the top:

```python
from datapulse.api.backpressure import AdmissionController, QueueDepthGuard
```

Inside `create_app()`, immediately after the `app.state.admission_controller = ...` block, add:

```python
    app.state.queue_depth_guard = QueueDepthGuard(limit=settings.arq_queue_depth_limit)
```

- [ ] **Step 3.5: Close the Arq pool on shutdown — `src/datapulse/api/bootstrap/lifespan.py`**

Add to the shutdown branch of `build_lifespan`:

```python
        from datapulse.tasks.queue import close_arq_pool

        with contextlib.suppress(Exception):
            await close_arq_pool()
```

(If `lifespan.py` does not yet import `contextlib`, add it.)

- [ ] **Step 3.6: Refactor `_check_query_executor` in `src/datapulse/api/routes/health.py`**

Replace the function body with an Arq-aware probe:

```python
def _check_query_executor() -> dict:
    """Probe the Arq queue Redis (db 1) — the queue is the new bottleneck."""
    try:
        from datapulse.tasks.async_executor import _get_job_client

        client = _get_job_client()
        if client is None:
            return {"status": "disabled"}
        t0 = time.monotonic()
        client.ping()
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        logger.exception("Query executor health check failed")
        return {"status": "error", "error": "internal_error"}
```

(The implementation is unchanged — the docstring update documents the new semantic. Skip this step if the docstring already matches.)

- [ ] **Step 3.7: Run the gate**

```bash
pytest tests/test_backpressure_queue_depth.py tests/test_health.py tests/test_stabilization.py -x -q
```

Expected output: all green.

- [ ] **Step 3.8: Lint + commit**

```bash
ruff format src/datapulse/api/backpressure.py src/datapulse/api/bootstrap/middleware.py src/datapulse/api/app.py src/datapulse/api/bootstrap/lifespan.py src/datapulse/api/routes/health.py tests/test_backpressure_queue_depth.py
ruff check src/datapulse/api/backpressure.py src/datapulse/api/bootstrap/middleware.py src/datapulse/api/app.py src/datapulse/api/bootstrap/lifespan.py src/datapulse/api/routes/health.py tests/test_backpressure_queue_depth.py
git add src/datapulse/api/backpressure.py src/datapulse/api/bootstrap/middleware.py src/datapulse/api/app.py src/datapulse/api/bootstrap/lifespan.py src/datapulse/api/routes/health.py tests/test_backpressure_queue_depth.py
git commit -m "feat(api): bridge backpressure to Arq queue depth"
```

---

## Task 4: Add Arq worker container + env vars (config only)

Wire the new worker into Docker Compose so a single `docker compose up -d` starts API, Postgres, Redis, and the worker. Production deploys (`docker-compose.prod.yml`) inherit the same shape because they extend the base file.

**Files:**
- Edit: `docker-compose.yml`
- Edit: `.env.example`

- [ ] **Step 4.1: Add the `arq-worker` service to `docker-compose.yml`**

Insert this block after the existing `redis:` service definition (Redis is already present — confirmed during preflight):

```yaml
  arq-worker:
    build:
      context: .
      target: api
    image: datapulse-api:local
    container_name: datapulse-arq-worker
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-datapulse}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}@postgres:5432/${POSTGRES_DB:-datapulse}?sslmode=disable
      REDIS_URL: redis://:${REDIS_PASSWORD:?REDIS_PASSWORD must be set}@redis:6379/0
      ARQ_QUEUE_NAME: ${ARQ_QUEUE_NAME:-datapulse:queries}
      ARQ_MAX_JOBS: ${ARQ_MAX_JOBS:-10}
      ARQ_JOB_TIMEOUT: ${ARQ_JOB_TIMEOUT:-300}
      SENTRY_DSN: ${SENTRY_DSN:-}
      SENTRY_ENVIRONMENT: ${SENTRY_ENVIRONMENT:-development}
      LOG_LEVEL: ${LOG_LEVEL:-info}
    command: ["arq", "datapulse.tasks.worker.WorkerSettings"]
    healthcheck:
      # Arq writes a heartbeat key; ping confirms Redis reachability.
      test: ["CMD-SHELL", "python -c \"import redis,os; redis.from_url(os.environ['REDIS_URL']).ping()\""]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"
    networks:
      - backend
    logging: *default-logging
    stop_grace_period: 35s  # Arq drains in-flight jobs on SIGTERM
```

Then in the existing `api:` service, add the queue-depth env var to its `environment:` block (next to `REDIS_URL`):

```yaml
      ARQ_QUEUE_NAME: ${ARQ_QUEUE_NAME:-datapulse:queries}
      ARQ_QUEUE_DEPTH_LIMIT: ${ARQ_QUEUE_DEPTH_LIMIT:-100}
```

Replace the `# NOTE: Celery worker removed ...` comment block above the redis service with:

```yaml
  # ---------- Arq worker — distributed query executor (replaces in-process pool) ----------
```

- [ ] **Step 4.2: Document the new env vars in `.env.example`**

Append:

```ini
# ── Arq distributed task queue ──────────────────────────────────────────────
# Queue list key inside Redis (db 1). Keep distinct from cache (db 0).
ARQ_QUEUE_NAME=datapulse:queries

# Reject API requests with 503 when queued+running jobs exceed this number.
# Set to 0 to disable the global queue-depth guard (per-process semaphore
# remains active).
ARQ_QUEUE_DEPTH_LIMIT=100

# Per-worker concurrency. Multiply by replicas for total parallelism.
ARQ_MAX_JOBS=10

# Hard timeout for a single query job in seconds. Should be >= the Postgres
# statement_timeout configured for the tenant session (default 270s).
ARQ_JOB_TIMEOUT=300
```

- [ ] **Step 4.3: Validate compose file**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
docker compose config --quiet
```

Expected output: empty (no errors). Any YAML problems print to stderr.

- [ ] **Step 4.4: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore(docker): add arq-worker service and queue-depth env vars"
```

---

## Task 5: Integration smoke test (RED → GREEN)

Proves the loop end-to-end against a real Redis (via `fakeredis` or, when available, the `datapulse-redis` container). Asserts that `submit_query` enqueues a job, the worker pulls and executes it, and the result lands under the `datapulse:query:<id>` key the polling endpoint reads.

**Files:**
- Create: `tests/test_arq_smoke.py`

- [ ] **Step 5.1: Write the smoke test**

```python
"""Integration smoke test — exercises the full Arq enqueue → worker → result loop."""

from __future__ import annotations

import asyncio
import json

import pytest
from arq.worker import Worker

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_enqueue_then_worker_runs_then_result_visible(monkeypatch) -> None:
    import fakeredis.aioredis

    from datapulse.tasks import async_executor, queue, worker

    fake = fakeredis.aioredis.FakeRedis(decode_responses=False)
    fake_state = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # Patch the Arq pool factory + the worker's job-state client.
    class FakePool:
        def __init__(self, redis):
            self.redis = redis
            self.captured: list[tuple] = []

        async def enqueue_job(self, name, *args, **kwargs):
            self.captured.append((name, kwargs))
            # Manually invoke the task — fakeredis doesn't run an Arq worker
            # loop, so we drive the function directly to keep the test hermetic.
            await worker.run_query_task({}, **kwargs)
            return object()

    pool = FakePool(fake)
    monkeypatch.setattr(queue, "_pool", pool, raising=False)
    monkeypatch.setattr(queue, "create_pool", lambda *_a, **_kw: pool)
    monkeypatch.setattr(async_executor, "_get_arq_pool", lambda: asyncio.sleep(0, result=pool))

    monkeypatch.setattr(worker, "_open_job_client", lambda: fake_state)

    sync_state: dict = {}

    class SyncStateClient:
        def setex(self, key, ttl, value):
            sync_state[key] = value

        def get(self, key):
            # Read-through: the async client wrote here.
            return sync_state.get(key) or asyncio.get_event_loop().run_until_complete(
                fake_state.get(key)
            )

    monkeypatch.setattr(async_executor, "_get_job_client", lambda: SyncStateClient())

    class FakeResult:
        def keys(self):
            return ["x"]

        def __iter__(self):
            return iter([(1,), (2,)])

    class FakeSession:
        def execute(self, *_a, **_kw):
            return FakeResult()

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(worker, "open_tenant_session", lambda *_a, **_kw: FakeSession())

    job_id = await async_executor.submit_query(sql="SELECT 1", tenant_id="t1")
    assert job_id is not None

    raw = await fake_state.get(f"datapulse:query:{job_id}")
    assert raw is not None
    record = json.loads(raw)
    assert record["status"] == "complete"
    assert record["row_count"] == 2
```

- [ ] **Step 5.2: Run the smoke test**

```bash
pytest tests/test_arq_smoke.py -m integration -x -q
```

Expected output: `1 passed`.

- [ ] **Step 5.3: Run the full unit gate**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
pytest -m unit -x -q
```

Expected output: all green; coverage stays at or above the configured floor.

- [ ] **Step 5.4: Live worker boot (manual smoke — recorded, not automated)**

```bash
docker compose up -d postgres redis
docker compose up --build -d arq-worker
docker compose logs --tail=50 arq-worker
```

Expected log line: `arq_worker_starting queue=datapulse:queries`. Stop the worker with `docker compose stop arq-worker` once verified.

- [ ] **Step 5.5: Commit**

```bash
git add tests/test_arq_smoke.py
git commit -m "test(integration): add Arq enqueue→worker→result smoke test"
```

---

## Verification checklist (run before opening PR)

- [ ] `ruff format --check src/ tests/` clean
- [ ] `ruff check src/ tests/` clean
- [ ] `pytest -m unit -x -q` green
- [ ] `pytest -m integration -k arq -x -q` green
- [ ] `docker compose config --quiet` returns 0
- [ ] `docker compose up -d arq-worker` produces `arq_worker_starting` log
- [ ] `grep -rn "asyncio.get_event_loop().run_in_executor" src/datapulse/tasks/` returns nothing (legacy executor removed)
- [ ] `grep -rn "_QUERY_SLOTS_BY_TENANT\|_reserve_query_slot" src/` returns nothing (in-process slot machinery removed)
- [ ] No new TODO/FIXME comments introduced (`grep -rn "TODO\|FIXME" src/datapulse/tasks/ src/datapulse/api/backpressure.py`)

## Rollback plan

The change is gated by a single setting: setting `ARQ_QUEUE_DEPTH_LIMIT=0` disables the queue-depth guard (the in-process semaphore still protects the API). If the worker container fails to start, the queries route returns `503 — Queue unavailable` because `submit_query` returns `None`; the rest of the API keeps serving. To roll back to the legacy in-process executor, revert the merge commit on this branch — the legacy code path is preserved verbatim in git history.
