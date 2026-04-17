"""Repository for sync_schedules table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class SyncScheduleRepository:
    """Data access for sync_schedules (Phase 2 — cron-based auto-sync)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        tenant_id: int,
        connection_id: int,
        cron_expr: str,
        is_active: bool = True,
        created_by: str | None = None,
    ) -> dict:
        """Insert a new sync_schedule row and return it."""
        stmt = text("""
            INSERT INTO public.sync_schedules
                (tenant_id, connection_id, cron_expr, is_active, created_by)
            VALUES
                (:tenant_id, :connection_id, :cron_expr, :is_active, :created_by)
            RETURNING id, tenant_id, connection_id, cron_expr, is_active,
                      last_run_at, created_by, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "connection_id": connection_id,
                    "cron_expr": cron_expr,
                    "is_active": is_active,
                    "created_by": created_by,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info(
            "sync_schedule_created",
            tenant_id=tenant_id,
            connection_id=connection_id,
            cron_expr=cron_expr,
        )
        return dict(row)

    def list_for_connection(
        self,
        connection_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """List schedules for a specific connection (RLS-scoped)."""
        count_sql = text("""
            SELECT COUNT(*) FROM public.sync_schedules
            WHERE connection_id = :cid
        """)
        total = self._session.execute(count_sql, {"cid": connection_id}).scalar() or 0

        sql = text("""
            SELECT id, tenant_id, connection_id, cron_expr, is_active,
                   last_run_at, created_by, created_at, updated_at
            FROM public.sync_schedules
            WHERE connection_id = :cid
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = (
            self._session.execute(
                sql,
                {"cid": connection_id, "limit": page_size, "offset": (page - 1) * page_size},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows], total

    def list_all_active(self) -> list[dict]:
        """Return all is_active=true schedules across all tenants.

        Used by the scheduler at startup to register APScheduler jobs.
        Note: no RLS tenant filter — called from the scheduler process,
        not from a tenant request context.
        """
        stmt = text("""
            SELECT id, tenant_id, connection_id, cron_expr, is_active,
                   last_run_at, created_by, created_at, updated_at
            FROM public.sync_schedules
            WHERE is_active = true
            ORDER BY id
        """)
        rows = self._session.execute(stmt).mappings().all()
        return [dict(r) for r in rows]

    def get(self, schedule_id: int) -> dict | None:
        stmt = text("""
            SELECT id, tenant_id, connection_id, cron_expr, is_active,
                   last_run_at, created_by, created_at, updated_at
            FROM public.sync_schedules
            WHERE id = :id
        """)
        row = self._session.execute(stmt, {"id": schedule_id}).mappings().fetchone()
        return dict(row) if row else None

    def delete(self, schedule_id: int) -> bool:
        """Hard-delete a schedule row. Returns True if a row was deleted."""
        stmt = text("DELETE FROM public.sync_schedules WHERE id = :id RETURNING id")
        row = self._session.execute(stmt, {"id": schedule_id}).fetchone()
        if row:
            log.info("sync_schedule_deleted", schedule_id=schedule_id)
        return row is not None

    def update_last_run(self, schedule_id: int) -> None:
        """Stamp last_run_at = now() after a scheduled job fires."""
        stmt = text("""
            UPDATE public.sync_schedules
            SET last_run_at = now(), updated_at = now()
            WHERE id = :id
        """)
        self._session.execute(stmt, {"id": schedule_id})
