"""SyncService — sync-job execution, history, schedules, and health summary."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from datapulse.control_center.models import (
    HealthSummary,
    SourceConnection,
    SyncJob,
    SyncJobList,
    SyncSchedule,
    SyncScheduleList,
)
from datapulse.control_center.repository import (
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
    SyncScheduleRepository,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class SyncService:
    """Sync-job execution, sync history, cron schedules, and health summary."""

    def __init__(
        self,
        session: Session,
        *,
        connections: SourceConnectionRepository,
        sync_jobs: SyncJobRepository,
        schedules: SyncScheduleRepository,
        releases: PipelineReleaseRepository,
    ) -> None:
        self._session = session
        self._connections = connections
        self._sync_jobs = sync_jobs
        self._schedules = schedules
        self._releases = releases

    def _get_connection(self, connection_id: int) -> SourceConnection | None:
        row = self._connections.get(connection_id)
        return SourceConnection(**row) if row else None

    # ── Sync jobs ────────────────────────────────────────────────────────────

    def trigger_sync(
        self,
        connection_id: int,
        *,
        tenant_id: int,
        run_mode: str = "manual",
        release_id: int | None = None,
        profile_id: int | None = None,
        created_by: str | None = None,
    ) -> SyncJob:
        """Create a sync_job for the connection and return it.

        Generates a new UUID for the pipeline_run_id so downstream
        listeners can correlate the run when execution is wired up.
        """
        conn = self._get_connection(connection_id)
        if conn is None:
            raise ValueError("connection_not_found")

        # Generate a stable run id — the actual pipeline_runs row may be
        # created asynchronously when a worker picks this up.
        run_id = str(uuid.uuid4())

        row = self._sync_jobs.create(
            tenant_id=tenant_id,
            source_connection_id=connection_id,
            run_mode=run_mode,
            pipeline_run_id=run_id,
            release_id=release_id,
            profile_id=profile_id,
            created_by=created_by,
        )
        log.info(
            "control_center.sync.triggered",
            tenant_id=tenant_id,
            connection_id=connection_id,
            run_id=run_id,
        )
        return SyncJob(**row)

    def list_sync_history(
        self,
        *,
        connection_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> SyncJobList:
        rows, total = self._sync_jobs.list_for_connection(
            connection_id, page=page, page_size=page_size
        )
        return SyncJobList(
            items=[SyncJob(**r) for r in rows],
            total=total,
        )

    # ── Sync schedules ───────────────────────────────────────────────────────

    def create_schedule(
        self,
        *,
        connection_id: int,
        tenant_id: int,
        cron_expr: str,
        is_active: bool = True,
        created_by: str | None = None,
    ) -> SyncSchedule:
        """Create a cron schedule for a source connection.

        Raises ``ValueError`` when the connection is not found.
        """
        conn = self._get_connection(connection_id)
        if conn is None:
            raise ValueError("connection_not_found")

        row = self._schedules.create(
            tenant_id=tenant_id,
            connection_id=connection_id,
            cron_expr=cron_expr,
            is_active=is_active,
            created_by=created_by,
        )
        log.info(
            "control_center.schedule.created",
            tenant_id=tenant_id,
            connection_id=connection_id,
            cron_expr=cron_expr,
        )
        return SyncSchedule(**row)

    def list_schedules(
        self,
        *,
        connection_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> SyncScheduleList:
        """List cron schedules for a source connection."""
        rows, total = self._schedules.list_for_connection(
            connection_id, page=page, page_size=page_size
        )
        return SyncScheduleList(
            items=[SyncSchedule(**r) for r in rows],
            total=total,
        )

    def delete_schedule(self, schedule_id: int) -> bool:
        """Hard-delete a sync schedule.

        Returns True if the schedule was found and deleted.
        """
        deleted = self._schedules.delete(schedule_id)
        if deleted:
            log.info("control_center.schedule.deleted", schedule_id=schedule_id)
        return deleted

    # ── Health summary ───────────────────────────────────────────────────────

    def get_health_summary(self, *, tenant_id: int) -> HealthSummary:
        """Return aggregated health data for the Control Center dashboard."""
        row = self._releases.get_health_summary(tenant_id)
        return HealthSummary(**row)
