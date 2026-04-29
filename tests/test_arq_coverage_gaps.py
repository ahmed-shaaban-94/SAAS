"""Cover the residual untested branches in tasks/queue.py, worker.py, async_executor.py.

These tests target specific missing-line gaps reported by the coverage run on
2026-04-29 — they are not happy-path tests (those live in test_arq_*.py) but
defensive-branch tests for URL parsing, error handling, and lifecycle hooks.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ─────────────────────────── tasks/worker.py ───────────────────────────


def test_job_state_url_falls_back_when_redis_url_unset(monkeypatch) -> None:
    """worker._job_state_url returns a default localhost URL when redis_url is empty."""
    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="", query_job_ttl=300)
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    assert worker._job_state_url() == "redis://localhost:6379/2"


def test_job_state_url_replaces_db_suffix(monkeypatch) -> None:
    """When redis_url ends in a numeric db, swap it for db 2."""
    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="redis://r:1234/0")
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    assert worker._job_state_url() == "redis://r:1234/2"


def test_job_state_url_appends_db_when_missing(monkeypatch) -> None:
    """When redis_url has no numeric db suffix, append /2."""
    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="redis://r:1234")
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    assert worker._job_state_url() == "redis://r:1234/2"


def test_open_job_client_returns_redis_client(monkeypatch) -> None:
    """_open_job_client builds a Redis client via from_url."""
    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="redis://localhost:6379/0", query_job_ttl=60)
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    client = worker._open_job_client()
    assert client is not None
    # redis.asyncio.Redis instance — not asserting specific class to avoid
    # tying tests to redis-py internals.


def test_redis_settings_uses_default_when_redis_url_empty(monkeypatch) -> None:
    """_redis_settings returns default RedisSettings when redis_url is empty."""
    from arq.connections import RedisSettings

    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="")
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    rs = worker._redis_settings()
    assert isinstance(rs, RedisSettings)


def test_redis_settings_replaces_db_suffix(monkeypatch) -> None:
    """When redis_url ends in /0, swap to /1 for the queue db."""
    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="redis://r:1234/0")
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    rs = worker._redis_settings()
    assert rs.database == 1


def test_redis_settings_appends_db_when_missing(monkeypatch) -> None:
    """When redis_url has no numeric db suffix, append /1."""
    from datapulse.tasks import worker

    fake_settings = MagicMock(redis_url="redis://r:1234")
    monkeypatch.setattr(worker, "get_settings", lambda: fake_settings)

    rs = worker._redis_settings()
    assert rs.database == 1


@pytest.mark.asyncio
async def test_run_query_task_truncates_when_row_limit_exceeded(monkeypatch) -> None:
    """run_query_task sets truncated=True and stops at cap."""
    import fakeredis.aioredis

    from datapulse.tasks import worker

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker, "_open_job_client", lambda: fake)

    class FakeResult:
        def keys(self):
            return ["id"]

        def __iter__(self):
            return iter([(i,) for i in range(50)])

    class FakeSession:
        def execute(self, *_a, **_kw):
            return FakeResult()

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(worker, "open_tenant_session", lambda tenant_id, timeout_s: FakeSession())

    await worker.run_query_task(
        {}, job_id="job-trunc", sql="SELECT id", params=None, tenant_id="t1", row_limit=5
    )

    record = json.loads(await fake.get("datapulse:query:job-trunc"))
    assert record["status"] == "complete"
    assert record["truncated"] is True
    assert record["row_count"] == 5


@pytest.mark.asyncio
async def test_run_query_task_translates_statement_timeout(monkeypatch) -> None:
    """run_query_task rewrites the asyncpg timeout error to 'Query timed out'."""
    import fakeredis.aioredis

    from datapulse.tasks import worker

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker, "_open_job_client", lambda: fake)

    class TimeoutSession:
        def execute(self, *_a, **_kw):
            raise RuntimeError("canceling statement due to statement timeout")

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        worker, "open_tenant_session", lambda tenant_id, timeout_s: TimeoutSession()
    )

    await worker.run_query_task(
        {}, job_id="job-to", sql="SELECT 1", params=None, tenant_id="t1", row_limit=10
    )

    record = json.loads(await fake.get("datapulse:query:job-to"))
    assert record["status"] == "failed"
    assert record["error"] == "Query timed out"


@pytest.mark.asyncio
async def test_on_startup_and_shutdown_log(monkeypatch) -> None:
    """Lifecycle hooks call the structured logger without raising."""
    from datapulse.tasks import worker

    info_calls: list = []
    fake_log = MagicMock()
    fake_log.info = lambda *a, **kw: info_calls.append((a, kw))
    monkeypatch.setattr(worker, "log", fake_log)

    await worker._on_startup({})
    await worker._on_shutdown({})

    assert any("starting" in (call[0][0] if call[0] else "") for call in info_calls)
    assert any("stopping" in (call[0][0] if call[0] else "") for call in info_calls)


# ─────────────────────────── tasks/queue.py ────────────────────────────


@pytest.mark.asyncio
async def test_get_arq_pool_returns_none_on_create_error(monkeypatch) -> None:
    """If create_pool raises, the singleton stays None and we surface None."""
    from datapulse.tasks import queue as queue_mod

    monkeypatch.setattr(queue_mod, "_pool", None, raising=False)

    async def boom(*_a, **_kw):
        raise RuntimeError("redis down")

    monkeypatch.setattr(queue_mod, "create_pool", boom)

    result = await queue_mod.get_arq_pool()
    assert result is None
    # Ensure the singleton wasn't poisoned with a partial value
    assert queue_mod._pool is None


@pytest.mark.asyncio
async def test_close_arq_pool_noop_when_pool_is_none(monkeypatch) -> None:
    """close_arq_pool short-circuits cleanly when no pool was created."""
    from datapulse.tasks import queue as queue_mod

    monkeypatch.setattr(queue_mod, "_pool", None, raising=False)
    await queue_mod.close_arq_pool()
    assert queue_mod._pool is None


@pytest.mark.asyncio
async def test_close_arq_pool_closes_and_resets(monkeypatch) -> None:
    """close_arq_pool calls pool.close() and resets the singleton to None."""
    from datapulse.tasks import queue as queue_mod

    fake_pool = AsyncMock()
    monkeypatch.setattr(queue_mod, "_pool", fake_pool, raising=False)

    await queue_mod.close_arq_pool()

    fake_pool.close.assert_awaited_once_with(close_connection_pool=True)
    assert queue_mod._pool is None


@pytest.mark.asyncio
async def test_close_arq_pool_resets_even_if_close_raises(monkeypatch) -> None:
    """The singleton is reset even when pool.close() raises."""
    from datapulse.tasks import queue as queue_mod

    fake_pool = AsyncMock()
    fake_pool.close.side_effect = RuntimeError("close failed")
    monkeypatch.setattr(queue_mod, "_pool", fake_pool, raising=False)

    with pytest.raises(RuntimeError):
        await queue_mod.close_arq_pool()
    assert queue_mod._pool is None


@pytest.mark.asyncio
async def test_queue_depth_returns_zcard_when_pool_available(monkeypatch) -> None:
    """queue_depth returns int(zcard(queue_name)) on the happy path."""
    from datapulse.tasks import queue as queue_mod

    fake_pool = AsyncMock()
    fake_pool.zcard = AsyncMock(return_value=7)

    async def fake_get_pool():
        return fake_pool

    monkeypatch.setattr(queue_mod, "get_arq_pool", fake_get_pool)

    depth = await queue_mod.queue_depth()
    assert depth == 7
    fake_pool.zcard.assert_awaited_once()


@pytest.mark.asyncio
async def test_queue_depth_returns_zero_when_pool_unavailable(monkeypatch) -> None:
    """queue_depth degrades to 0 when the pool cannot be created."""
    from datapulse.tasks import queue as queue_mod

    async def no_pool():
        return None

    monkeypatch.setattr(queue_mod, "get_arq_pool", no_pool)

    depth = await queue_mod.queue_depth()
    assert depth == 0


@pytest.mark.asyncio
async def test_queue_depth_returns_zero_on_zcard_error(monkeypatch) -> None:
    """queue_depth swallows a probe failure and returns 0."""
    from datapulse.tasks import queue as queue_mod

    fake_pool = AsyncMock()
    fake_pool.zcard = AsyncMock(side_effect=RuntimeError("redis down"))

    async def fake_get_pool():
        return fake_pool

    monkeypatch.setattr(queue_mod, "get_arq_pool", fake_get_pool)

    depth = await queue_mod.queue_depth()
    assert depth == 0


# ──────────────────────── tasks/async_executor.py ──────────────────────


@pytest.mark.asyncio
async def test_submit_query_returns_none_when_arq_pool_unavailable(monkeypatch) -> None:
    """submit_query returns None when _get_arq_pool yields None."""
    from datapulse.tasks import async_executor

    fake_client = MagicMock()
    fake_client.setex = MagicMock()
    monkeypatch.setattr(async_executor, "_get_job_client", lambda: fake_client)
    monkeypatch.setattr(async_executor, "_get_arq_pool", AsyncMock(return_value=None))

    result = await async_executor.submit_query("SELECT 1", tenant_id="t1", row_limit=10)
    assert result is None


@pytest.mark.asyncio
async def test_submit_query_raises_capacity_when_enqueue_fails(monkeypatch) -> None:
    """submit_query raises QueryCapacityExceededError when pool.enqueue_job fails."""
    from datapulse.tasks import async_executor

    fake_client = MagicMock()
    fake_client.setex = MagicMock()
    monkeypatch.setattr(async_executor, "_get_job_client", lambda: fake_client)

    fake_pool = AsyncMock()
    fake_pool.enqueue_job = AsyncMock(side_effect=RuntimeError("queue saturated"))
    monkeypatch.setattr(async_executor, "_get_arq_pool", AsyncMock(return_value=fake_pool))

    with pytest.raises(async_executor.QueryCapacityExceededError):
        await async_executor.submit_query("SELECT 1", tenant_id="t1", row_limit=10)


def test_get_job_result_returns_none_on_redis_error(monkeypatch) -> None:
    """get_job_result swallows Redis exceptions and returns None."""
    from datapulse.tasks import async_executor

    fake_client = MagicMock()
    fake_client.get = MagicMock(side_effect=RuntimeError("redis down"))
    monkeypatch.setattr(async_executor, "_get_job_client", lambda: fake_client)

    assert async_executor.get_job_result("job-x") is None
