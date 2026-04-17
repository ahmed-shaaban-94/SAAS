"""Repository for pipeline_releases table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class PipelineReleaseRepository:
    """Data access for pipeline_releases (append-only, read-only here)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        count_sql = text("SELECT COUNT(*) FROM public.pipeline_releases")
        total = self._session.execute(count_sql).scalar() or 0
        sql = text("""
            SELECT id, tenant_id, release_version, draft_id, source_release_id,
                   snapshot_json, release_notes, is_rollback, published_by, published_at
            FROM public.pipeline_releases
            ORDER BY release_version DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = (
            self._session.execute(sql, {"limit": page_size, "offset": (page - 1) * page_size})
            .mappings()
            .all()
        )
        return [dict(r) for r in rows], total

    def get(self, release_id: int) -> dict | None:
        stmt = text("""
            SELECT id, tenant_id, release_version, draft_id, source_release_id,
                   snapshot_json, release_notes, is_rollback, published_by, published_at
            FROM public.pipeline_releases
            WHERE id = :id
        """)
        row = self._session.execute(stmt, {"id": release_id}).mappings().fetchone()
        return dict(row) if row else None

    def latest(self) -> dict | None:
        """Most recent release for the current tenant (RLS-scoped)."""
        stmt = text("""
            SELECT id, tenant_id, release_version, draft_id, source_release_id,
                   snapshot_json, release_notes, is_rollback, published_by, published_at
            FROM public.pipeline_releases
            ORDER BY release_version DESC
            LIMIT 1
        """)
        row = self._session.execute(stmt).mappings().fetchone()
        return dict(row) if row else None

    def count_for_tenant(self, tenant_id: int) -> int:
        """Return the total number of releases for the given tenant."""
        stmt = text("SELECT COUNT(*) FROM public.pipeline_releases WHERE tenant_id = :tenant_id")
        return self._session.execute(stmt, {"tenant_id": tenant_id}).scalar() or 0

    def get_health_summary(self, tenant_id: int) -> dict:
        """Aggregate connection, release, draft, and sync data for the tenant.

        Returns a flat dict with keys:
          active_connections, last_sync_at, active_release_version,
          pending_drafts, failed_syncs_last_24h
        """
        stmt = text("""
            SELECT
                (
                    SELECT COUNT(*)
                    FROM public.source_connections
                    WHERE tenant_id = :tenant_id AND status = 'active'
                ) AS active_connections,
                (
                    SELECT MAX(last_sync_at)
                    FROM public.source_connections
                    WHERE tenant_id = :tenant_id
                ) AS last_sync_at,
                (
                    SELECT MAX(release_version)
                    FROM public.pipeline_releases
                    WHERE tenant_id = :tenant_id
                ) AS active_release_version,
                (
                    SELECT COUNT(*)
                    FROM public.pipeline_drafts
                    WHERE tenant_id = :tenant_id
                      AND status NOT IN ('published', 'publish_failed')
                ) AS pending_drafts,
                (
                    SELECT COUNT(*)
                    FROM public.sync_jobs sj
                    JOIN public.pipeline_runs pr ON pr.id = sj.pipeline_run_id
                    WHERE sj.tenant_id = :tenant_id
                      AND pr.status = 'failed'
                      AND sj.created_at >= now() - INTERVAL '24 hours'
                ) AS failed_syncs_last_24h
        """)
        row = self._session.execute(stmt, {"tenant_id": tenant_id}).mappings().fetchone()
        if row is None:
            return {
                "active_connections": 0,
                "last_sync_at": None,
                "active_release_version": None,
                "pending_drafts": 0,
                "failed_syncs_last_24h": 0,
            }
        return dict(row)

    # ── Write operations (Phase 1d — append-only) ───────────

    def create(
        self,
        *,
        tenant_id: int,
        draft_id: int | None = None,
        source_release_id: int | None = None,
        snapshot_json: dict,
        release_notes: str = "",
        is_rollback: bool = False,
        published_by: str | None = None,
    ) -> dict:
        """Insert a new release (always append, never UPDATE).

        The ``release_version`` is derived automatically as ``MAX(release_version) + 1``
        within the tenant's RLS scope.
        """
        stmt = text("""
            INSERT INTO public.pipeline_releases
                (tenant_id, release_version, draft_id, source_release_id,
                 snapshot_json, release_notes, is_rollback, published_by)
            VALUES (
                :tenant_id,
                COALESCE(
                    (SELECT MAX(release_version) + 1
                     FROM public.pipeline_releases
                     WHERE tenant_id = :tenant_id),
                    1
                ),
                :draft_id, :source_release_id,
                :snapshot_json::jsonb, :release_notes, :is_rollback, :published_by
            )
            RETURNING id, tenant_id, release_version, draft_id, source_release_id,
                      snapshot_json, release_notes, is_rollback, published_by, published_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "draft_id": draft_id,
                    "source_release_id": source_release_id,
                    "snapshot_json": json.dumps(snapshot_json),
                    "release_notes": release_notes,
                    "is_rollback": is_rollback,
                    "published_by": published_by,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info(
            "pipeline_release_created",
            tenant_id=tenant_id,
            is_rollback=is_rollback,
        )
        return dict(row)
