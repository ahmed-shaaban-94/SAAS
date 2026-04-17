"""Repository for pipeline_drafts table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class PipelineDraftRepository:
    """Data access for pipeline_drafts (state-machine workflow)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        tenant_id: int,
        entity_type: str,
        entity_id: int | None = None,
        draft_json: dict,
        created_by: str | None = None,
    ) -> dict:
        """Insert a new draft in 'draft' status and return the row."""
        stmt = text("""
            INSERT INTO public.pipeline_drafts
                (tenant_id, entity_type, entity_id, draft_json, created_by)
            VALUES
                (:tenant_id, :entity_type, :entity_id, :draft_json::jsonb, :created_by)
            RETURNING id, tenant_id, entity_type, entity_id, draft_json, status,
                      validation_report_json, preview_result_json, version,
                      created_by, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "draft_json": json.dumps(draft_json),
                    "created_by": created_by,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info("pipeline_draft_created", tenant_id=tenant_id, entity_type=entity_type)
        return dict(row)

    def get(self, draft_id: int) -> dict | None:
        stmt = text("""
            SELECT id, tenant_id, entity_type, entity_id, draft_json, status,
                   validation_report_json, preview_result_json, version,
                   created_by, created_at, updated_at
            FROM public.pipeline_drafts
            WHERE id = :id
        """)
        row = self._session.execute(stmt, {"id": draft_id}).mappings().fetchone()
        return dict(row) if row else None

    def list(self, *, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
        count_sql = text("SELECT COUNT(*) FROM public.pipeline_drafts")
        total = self._session.execute(count_sql).scalar() or 0
        sql = text("""
            SELECT id, tenant_id, entity_type, entity_id, draft_json, status,
                   validation_report_json, preview_result_json, version,
                   created_by, created_at, updated_at
            FROM public.pipeline_drafts
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = (
            self._session.execute(sql, {"limit": page_size, "offset": (page - 1) * page_size})
            .mappings()
            .all()
        )
        return [dict(r) for r in rows], total

    def update_status(self, draft_id: int, status: str) -> dict | None:
        """Advance the draft's status field."""
        stmt = text("""
            UPDATE public.pipeline_drafts
            SET status = :status, updated_at = now()
            WHERE id = :id
            RETURNING id, tenant_id, entity_type, entity_id, draft_json, status,
                      validation_report_json, preview_result_json, version,
                      created_by, created_at, updated_at
        """)
        row = self._session.execute(stmt, {"id": draft_id, "status": status}).mappings().fetchone()
        return dict(row) if row else None

    def update_validation(
        self, draft_id: int, *, status: str, validation_report_json: dict
    ) -> dict | None:
        """Persist the validation report and update status."""
        stmt = text("""
            UPDATE public.pipeline_drafts
            SET status = :status,
                validation_report_json = :vr::jsonb,
                updated_at = now()
            WHERE id = :id
            RETURNING id, tenant_id, entity_type, entity_id, draft_json, status,
                      validation_report_json, preview_result_json, version,
                      created_by, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "id": draft_id,
                    "status": status,
                    "vr": json.dumps(validation_report_json),
                },
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None

    def update_preview(
        self, draft_id: int, *, status: str, preview_result_json: dict
    ) -> dict | None:
        """Persist the preview result and update status."""
        stmt = text("""
            UPDATE public.pipeline_drafts
            SET status = :status,
                preview_result_json = :pr::jsonb,
                updated_at = now()
            WHERE id = :id
            RETURNING id, tenant_id, entity_type, entity_id, draft_json, status,
                      validation_report_json, preview_result_json, version,
                      created_by, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "id": draft_id,
                    "status": status,
                    "pr": json.dumps(preview_result_json),
                },
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None
