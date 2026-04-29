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

    seen: dict = {}

    class FakeStateClient:
        def setex(self, key, ttl, value):
            seen[key] = value

    monkeypatch.setattr(async_executor, "_get_job_client", lambda: FakeStateClient())

    job_id = await async_executor.submit_query(sql="SELECT 1", tenant_id="t1", row_limit=100)

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
