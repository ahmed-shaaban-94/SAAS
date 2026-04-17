"""Repository for mapping_templates table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class MappingTemplateRepository:
    """Data access for mapping_templates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        source_type: str | None = None,
        template_name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        params: dict = {}
        if source_type:
            conditions.append("source_type = :source_type")
            params["source_type"] = source_type
        if template_name:
            conditions.append("template_name ILIKE :template_name")
            params["template_name"] = f"%{template_name}%"

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        count_sql = text(f"SELECT COUNT(*) FROM public.mapping_templates {where}")  # noqa: S608
        total = self._session.execute(count_sql, params).scalar() or 0

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        sql = text(f"""
            SELECT id, tenant_id, source_type, template_name, source_schema_hash,
                   mapping_json, version, created_by, created_at, updated_at
            FROM public.mapping_templates
            {where}
            ORDER BY template_name, version DESC
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608
        rows = self._session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows], total

    def get(self, template_id: int) -> dict | None:
        stmt = text("""
            SELECT id, tenant_id, source_type, template_name, source_schema_hash,
                   mapping_json, version, created_by, created_at, updated_at
            FROM public.mapping_templates
            WHERE id = :id
        """)
        row = self._session.execute(stmt, {"id": template_id}).mappings().fetchone()
        return dict(row) if row else None

    # ── Write operations (Phase 1c) ──────────────────────────

    def create(
        self,
        *,
        tenant_id: int,
        source_type: str,
        template_name: str,
        mapping_json: dict,
        source_schema_hash: str | None = None,
        created_by: str | None = None,
    ) -> dict:
        """Insert a new mapping template (version 1) and return the row."""
        stmt = text("""
            INSERT INTO public.mapping_templates
                (tenant_id, source_type, template_name, mapping_json,
                 source_schema_hash, created_by)
            VALUES
                (:tenant_id, :source_type, :template_name, :mapping_json::jsonb,
                 :source_schema_hash, :created_by)
            RETURNING id, tenant_id, source_type, template_name, source_schema_hash,
                      mapping_json, version, created_by, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "source_type": source_type,
                    "template_name": template_name,
                    "mapping_json": json.dumps(mapping_json),
                    "source_schema_hash": source_schema_hash,
                    "created_by": created_by,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info("mapping_template_created", tenant_id=tenant_id, template_name=template_name)
        return dict(row)

    def update(
        self,
        template_id: int,
        *,
        template_name: str | None = None,
        mapping_json: dict | None = None,
    ) -> dict | None:
        """Update specified fields and bump the version. Returns updated row or None."""
        sets: list[str] = []
        params: dict = {"id": template_id}
        if template_name is not None:
            sets.append("template_name = :template_name")
            params["template_name"] = template_name
        if mapping_json is not None:
            sets.append("mapping_json = :mapping_json::jsonb")
            params["mapping_json"] = json.dumps(mapping_json)
        if not sets:
            return self.get(template_id)
        sets.extend(["version = version + 1", "updated_at = now()"])
        stmt = text(f"""
            UPDATE public.mapping_templates
            SET {", ".join(sets)}
            WHERE id = :id
            RETURNING id, tenant_id, source_type, template_name, source_schema_hash,
                      mapping_json, version, created_by, created_at, updated_at
        """)  # noqa: S608
        row = self._session.execute(stmt, params).mappings().fetchone()
        return dict(row) if row else None
