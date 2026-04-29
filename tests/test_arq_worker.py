"""Unit tests for the Arq worker module."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_worker_settings_exposes_required_attrs() -> None:
    from datapulse.tasks.worker import WorkerSettings

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
    import json

    import fakeredis.aioredis

    from datapulse.tasks import worker

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker, "_open_job_client", lambda: fake)

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

    monkeypatch.setattr(worker, "open_tenant_session", lambda tenant_id, timeout_s: FakeSession())

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

    monkeypatch.setattr(worker, "open_tenant_session", lambda tenant_id, timeout_s: BoomSession())

    await worker.run_query_task(
        {}, job_id="job-err", sql="SELECT 1", params=None, tenant_id="t1", row_limit=10
    )

    record = json.loads(await fake.get("datapulse:query:job-err"))
    assert record["status"] == "failed"
    assert "boom" in record["error"]
