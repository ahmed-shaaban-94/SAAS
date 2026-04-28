"""Integration smoke test — exercises the full Arq enqueue → worker → result loop."""

from __future__ import annotations

import asyncio
import json

import pytest

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
