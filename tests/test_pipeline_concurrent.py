"""Concurrent pipeline execution tests — H5.6.

Verifies that two simultaneous pipeline trigger calls:
  1. Each create a distinct run record (no record corruption).
  2. Do not overwrite each other's run_id.
  3. Can be individually completed without cross-contamination.

All DB operations are mocked so the tests run without a real database.
The concurrency is simulated via threading.Thread to expose race conditions
that sequential tests would miss (e.g. shared mutable state, global counters).
"""

from __future__ import annotations

import threading
from unittest.mock import create_autospec
from uuid import UUID, uuid4

from datapulse.pipeline.models import (
    PipelineRunCreate,
    PipelineRunResponse,
    PipelineRunUpdate,
)
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_response(run_id: UUID | None = None, tenant_id: int = 1) -> PipelineRunResponse:
    """Build a minimal PipelineRunResponse for mock return values."""
    from datetime import UTC, datetime

    rid = run_id or uuid4()
    return PipelineRunResponse(
        id=rid,
        run_type="bronze",
        status="running",
        trigger_source=None,
        started_at=datetime.now(UTC),
        finished_at=None,
        duration_seconds=None,
        rows_loaded=None,
        error_message=None,
        metadata={},
        tenant_id=tenant_id,
    )


# ---------------------------------------------------------------------------
# H5.6.1 — Two concurrent start_run calls produce distinct run IDs
# ---------------------------------------------------------------------------


class TestConcurrentPipelineStart:
    def test_two_concurrent_starts_produce_distinct_run_ids(self) -> None:
        """Two threads calling start_run simultaneously must receive different run IDs.

        Failure mode this test guards against: a global/shared ID counter that
        is read-then-incremented non-atomically, causing both threads to receive
        the same run_id (last-write-wins corruption).
        """
        mock_repo = create_autospec(PipelineRepository, instance=True)

        run_id_a = uuid4()
        run_id_b = uuid4()
        # Side-effect returns a different response on each call (thread A then B or vice versa)
        mock_repo.create_run.side_effect = [
            _make_run_response(run_id_a),
            _make_run_response(run_id_b),
        ]

        service = PipelineService(mock_repo)
        results: list[PipelineRunResponse] = []
        lock = threading.Lock()

        def trigger(tenant_id: int) -> None:
            data = PipelineRunCreate(run_type="bronze")
            result = service.start_run(data, tenant_id=tenant_id)
            with lock:
                results.append(result)

        threads = [
            threading.Thread(target=trigger, args=(1,)),
            threading.Thread(target=trigger, args=(2,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 2, "Both threads must complete successfully"
        ids = {r.id for r in results}
        assert len(ids) == 2, (
            f"Expected 2 distinct run IDs, got {ids}. "
            "Concurrent start_run calls must not share a run_id."
        )

    def test_concurrent_starts_call_create_run_twice(self) -> None:
        """The repository's create_run method must be called exactly once per trigger."""
        mock_repo = create_autospec(PipelineRepository, instance=True)
        mock_repo.create_run.side_effect = [
            _make_run_response(),
            _make_run_response(),
        ]

        service = PipelineService(mock_repo)

        barrier = threading.Barrier(2)  # ensure both threads enter simultaneously

        def trigger() -> None:
            barrier.wait()  # synchronise entry
            data = PipelineRunCreate(run_type="bronze")
            service.start_run(data, tenant_id=1)

        threads = [threading.Thread(target=trigger) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert mock_repo.create_run.call_count == 2, (
            "create_run must be called once per concurrent trigger, not conflated into one."
        )


# ---------------------------------------------------------------------------
# H5.6.2 — Two concurrent complete_run calls for different runs don't cross-update
# ---------------------------------------------------------------------------


class TestConcurrentPipelineComplete:
    def test_two_concurrent_completions_target_correct_run_ids(self) -> None:
        """Two threads completing different runs must update their own run_id only."""
        mock_repo = create_autospec(PipelineRepository, instance=True)

        run_id_a = uuid4()
        run_id_b = uuid4()

        # get_run returns a running response for whichever ID is queried
        def fake_get_run(rid: UUID) -> PipelineRunResponse:
            return _make_run_response(rid)

        mock_repo.get_run.side_effect = fake_get_run
        mock_repo.update_run.return_value = _make_run_response()

        service = PipelineService(mock_repo)
        completed_ids: list[UUID] = []
        lock = threading.Lock()

        def complete(run_id: UUID) -> None:
            service.complete_run(run_id, rows_loaded=1000)
            with lock:
                completed_ids.append(run_id)

        threads = [
            threading.Thread(target=complete, args=(run_id_a,)),
            threading.Thread(target=complete, args=(run_id_b,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(completed_ids) == 2, "Both completions must succeed"

        # update_run must have been called for each run_id exactly once
        update_call_args = [call.args[0] for call in mock_repo.update_run.call_args_list]
        assert run_id_a in update_call_args, "run_id_a must be updated"
        assert run_id_b in update_call_args, "run_id_b must be updated"


# ---------------------------------------------------------------------------
# H5.6.3 — Concurrent update_status calls don't intermix statuses
# ---------------------------------------------------------------------------


class TestConcurrentStatusUpdate:
    def test_concurrent_status_updates_preserve_correct_status(self) -> None:
        """Two concurrent update_status calls for different runs must not swap statuses."""
        mock_repo = create_autospec(PipelineRepository, instance=True)

        run_id_a = uuid4()
        run_id_b = uuid4()

        # Record which run_id was updated with which status
        updates: dict[UUID, str] = {}
        update_lock = threading.Lock()

        def fake_update(rid: UUID, data: PipelineRunUpdate) -> PipelineRunResponse:
            with update_lock:
                updates[rid] = data.status
            return _make_run_response(rid)

        mock_repo.update_run.side_effect = fake_update
        service = PipelineService(mock_repo)

        def update(run_id: UUID, status: str) -> None:
            upd = PipelineRunUpdate(status=status)
            service.update_status(run_id, upd)

        threads = [
            threading.Thread(target=update, args=(run_id_a, "running")),
            threading.Thread(target=update, args=(run_id_b, "failed")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert updates.get(run_id_a) == "running", (
            f"run_a must have status 'running', got {updates.get(run_id_a)!r}"
        )
        assert updates.get(run_id_b) == "failed", (
            f"run_b must have status 'failed', got {updates.get(run_id_b)!r}"
        )
