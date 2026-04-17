"""Tests for SyncSchedule CRUD and APScheduler wiring (Phase 2).

Uses in-memory SQLite (via SQLAlchemy) where possible; for operations
that need PostgreSQL syntax (RETURNING, RLS), the DB calls are mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from datapulse.control_center.models import SyncSchedule, SyncScheduleList

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_schedule_row(
    schedule_id: int = 1,
    connection_id: int = 10,
    tenant_id: int = 1,
    cron_expr: str = "0 6 * * *",
    is_active: bool = True,
) -> dict:
    now = datetime.now(UTC)
    return {
        "id": schedule_id,
        "tenant_id": tenant_id,
        "connection_id": connection_id,
        "cron_expr": cron_expr,
        "is_active": is_active,
        "last_run_at": None,
        "created_by": "user@example.com",
        "created_at": now,
        "updated_at": now,
    }


def _make_connection_row(connection_id: int = 10) -> dict:
    now = datetime.now(UTC)
    return {
        "id": connection_id,
        "tenant_id": 1,
        "name": "Test Sheet",
        "source_type": "google_sheets",
        "status": "active",
        "config_json": {"spreadsheet_id": "abc"},
        "credentials_ref": None,
        "last_sync_at": None,
        "created_by": "user@example.com",
        "created_at": now,
        "updated_at": now,
    }


def _make_service(
    *,
    connection_row: dict | None = None,
    schedule_rows: list[dict] | None = None,
    created_schedule: dict | None = None,
    delete_result: bool = True,
):
    """Build a ControlCenterService with mocked repositories."""
    from datapulse.control_center.repository import (
        MappingTemplateRepository,
        PipelineDraftRepository,
        PipelineProfileRepository,
        PipelineReleaseRepository,
        SourceConnectionRepository,
        SyncJobRepository,
        SyncScheduleRepository,
    )
    from datapulse.control_center.service import ControlCenterService

    session = MagicMock()

    conn_repo = MagicMock(spec=SourceConnectionRepository)
    conn_repo.get.return_value = connection_row or _make_connection_row()

    sched_repo = MagicMock(spec=SyncScheduleRepository)
    sched_repo.create.return_value = created_schedule or _make_schedule_row()
    rows = schedule_rows or [_make_schedule_row()]
    sched_repo.list_for_connection.return_value = (rows, len(rows))
    sched_repo.delete.return_value = delete_result

    return ControlCenterService(
        session,
        connections=conn_repo,
        profiles=MagicMock(spec=PipelineProfileRepository),
        mappings=MagicMock(spec=MappingTemplateRepository),
        releases=MagicMock(spec=PipelineReleaseRepository),
        sync_jobs=MagicMock(spec=SyncJobRepository),
        drafts=MagicMock(spec=PipelineDraftRepository),
        schedules=sched_repo,
    )


# ---------------------------------------------------------------------------
# Service: create_schedule
# ---------------------------------------------------------------------------


def test_create_schedule_ok():
    svc = _make_service()
    result = svc.create_schedule(
        connection_id=10,
        tenant_id=1,
        cron_expr="0 6 * * *",
        created_by="user@example.com",
    )
    assert isinstance(result, SyncSchedule)
    assert result.cron_expr == "0 6 * * *"
    assert result.is_active is True


def test_create_schedule_connection_not_found():
    svc = _make_service(connection_row=None)
    svc._sync._connections.get.return_value = None
    with pytest.raises(ValueError, match="connection_not_found"):
        svc.create_schedule(connection_id=99, tenant_id=1, cron_expr="0 * * * *")


def test_create_schedule_inactive():
    row = _make_schedule_row(is_active=False)
    svc = _make_service(created_schedule=row)
    result = svc.create_schedule(
        connection_id=10,
        tenant_id=1,
        cron_expr="0 6 * * *",
        is_active=False,
    )
    assert result.is_active is False


# ---------------------------------------------------------------------------
# Service: list_schedules
# ---------------------------------------------------------------------------


def test_list_schedules_returns_list():
    rows = [_make_schedule_row(i) for i in range(1, 4)]
    svc = _make_service(schedule_rows=rows)
    result = svc.list_schedules(connection_id=10)
    assert isinstance(result, SyncScheduleList)
    assert result.total == 3  # noqa: PLR2004
    assert len(result.items) == 3  # noqa: PLR2004


def test_list_schedules_empty():
    svc = _make_service(schedule_rows=[])
    svc._sync._schedules.list_for_connection.return_value = ([], 0)
    result = svc.list_schedules(connection_id=10)
    assert result.total == 0
    assert result.items == []


# ---------------------------------------------------------------------------
# Service: delete_schedule
# ---------------------------------------------------------------------------


def test_delete_schedule_ok():
    svc = _make_service(delete_result=True)
    assert svc.delete_schedule(1) is True


def test_delete_schedule_not_found():
    svc = _make_service(delete_result=False)
    assert svc.delete_schedule(999) is False


# ---------------------------------------------------------------------------
# SyncScheduleRepository (unit-test the repo methods in isolation)
# ---------------------------------------------------------------------------


def test_repo_create_calls_execute():
    from datapulse.control_center.repository import SyncScheduleRepository

    session = MagicMock()
    row_mock = MagicMock()
    row_mock.__iter__ = MagicMock(return_value=iter(_make_schedule_row().items()))

    # Make session.execute(...).mappings().fetchone() return a dict-like object
    mapping_mock = MagicMock()
    mapping_mock.fetchone.return_value = _make_schedule_row()
    session.execute.return_value.mappings.return_value = mapping_mock

    repo = SyncScheduleRepository(session)
    result = repo.create(
        tenant_id=1,
        connection_id=10,
        cron_expr="0 6 * * *",
        created_by="user@example.com",
    )
    assert session.execute.called
    assert result["cron_expr"] == "0 6 * * *"


def test_repo_delete_calls_execute():
    from datapulse.control_center.repository import SyncScheduleRepository

    session = MagicMock()
    session.execute.return_value.fetchone.return_value = (1,)

    repo = SyncScheduleRepository(session)
    deleted = repo.delete(1)
    assert deleted is True
    assert session.execute.called


def test_repo_list_all_active_no_filter():
    from datapulse.control_center.repository import SyncScheduleRepository

    session = MagicMock()
    rows = [_make_schedule_row(i) for i in range(1, 3)]
    session.execute.return_value.mappings.return_value.all.return_value = rows

    repo = SyncScheduleRepository(session)
    result = repo.list_all_active()
    assert len(result) == 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# APScheduler wiring: _register_sync_schedules
# ---------------------------------------------------------------------------


def test_register_sync_schedules_registers_jobs():
    """_register_sync_schedules() should add one APScheduler job per active schedule."""
    from datapulse.scheduler import _register_sync_schedules, scheduler

    fake_schedules = [
        _make_schedule_row(1, cron_expr="0 6 * * *"),
        _make_schedule_row(2, cron_expr="30 8 * * 1"),
    ]

    mock_repo = MagicMock()
    mock_repo.list_all_active.return_value = fake_schedules

    with (
        # Patch at the source module because _register_sync_schedules uses lazy imports
        patch("datapulse.core.db.get_session_factory", return_value=lambda: MagicMock()),
        patch(
            "datapulse.control_center.repository.SyncScheduleRepository",
            return_value=mock_repo,
        ),
        patch.object(scheduler, "add_job") as mock_add_job,
    ):
        n = _register_sync_schedules()

    assert n == 2  # noqa: PLR2004
    assert mock_add_job.call_count == 2  # noqa: PLR2004


def test_register_sync_schedules_skips_bad_cron():
    """Schedules with malformed cron expressions should be skipped (not crash)."""
    from datapulse.scheduler import _register_sync_schedules, scheduler

    bad_schedule = _make_schedule_row(1, cron_expr="not-a-cron")

    mock_repo = MagicMock()
    mock_repo.list_all_active.return_value = [bad_schedule]

    with (
        patch("datapulse.core.db.get_session_factory", return_value=lambda: MagicMock()),
        patch(
            "datapulse.control_center.repository.SyncScheduleRepository",
            return_value=mock_repo,
        ),
        patch.object(scheduler, "add_job") as mock_add_job,
    ):
        n = _register_sync_schedules()

    assert n == 0
    assert mock_add_job.call_count == 0


def test_register_sync_schedules_db_error_is_graceful():
    """DB failures should be caught and return 0 without crashing."""
    from datapulse.scheduler import _register_sync_schedules

    with (
        patch("datapulse.core.db.get_session_factory", return_value=lambda: MagicMock()),
        patch(
            "datapulse.control_center.repository.SyncScheduleRepository",
            side_effect=Exception("DB unavailable"),
        ),
    ):
        n = _register_sync_schedules()

    assert n == 0


# ---------------------------------------------------------------------------
# _make_sync_job_fn produces a callable
# ---------------------------------------------------------------------------


def test_make_sync_job_fn_returns_coroutine():
    import inspect

    from datapulse.scheduler import _make_sync_job_fn

    fn = _make_sync_job_fn(connection_id=10, tenant_id=1, schedule_id=1)
    assert callable(fn)
    coro = fn()
    assert inspect.iscoroutine(coro)
    coro.close()  # clean up without running
