"""Repository for sync_jobs table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class SyncJobRepository:
    """Data access for sync_jobs — always JOIN with pipeline_runs for status."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        tenant_id: int,
        source_connection_id: int,
        run_mode: str,
        pipeline_run_id: str | None = None,
        release_id: int | None = None,
        profile_id: int | None = None,
        created_by: str | None = None,
    ) -> dict:
        """Insert a new sync_job row and return it."""
        stmt = text("""
            INSERT INTO public.sync_jobs
                (tenant_id, source_connection_id, run_mode,
                 pipeline_run_id, release_id, profile_id, created_by)
            VALUES
                (:tenant_id, :source_connection_id, :run_mode,
                 :pipeline_run_id::uuid, :release_id, :profile_id, :created_by)
            RETURNING id, tenant_id, pipeline_run_id::text AS pipeline_run_id,
                      source_connection_id, release_id, profile_id,
                      run_mode, created_by, created_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "source_connection_id": source_connection_id,
                    "run_mode": run_mode,
                    "pipeline_run_id": pipeline_run_id,
                    "release_id": release_id,
                    "profile_id": profile_id,
                    "created_by": created_by,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info(
            "sync_job_created",
            tenant_id=tenant_id,
            source_connection_id=source_connection_id,
            run_mode=run_mode,
        )
        return dict(row)

    def list_for_connection(
        self,
        connection_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        count_sql = text("""
            SELECT COUNT(*)
            FROM public.sync_jobs
            WHERE source_connection_id = :cid
        """)
        total = self._session.execute(count_sql, {"cid": connection_id}).scalar() or 0

        sql = text("""
            SELECT sj.id, sj.tenant_id, sj.pipeline_run_id::text AS pipeline_run_id,
                   sj.source_connection_id, sj.release_id, sj.profile_id,
                   sj.run_mode, sj.created_by, sj.created_at,
                   pr.status, pr.rows_loaded, pr.error_message,
                   pr.started_at, pr.finished_at, pr.duration_seconds
            FROM public.sync_jobs sj
            LEFT JOIN public.pipeline_runs pr ON pr.id = sj.pipeline_run_id
            WHERE sj.source_connection_id = :cid
            ORDER BY sj.created_at DESC
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
