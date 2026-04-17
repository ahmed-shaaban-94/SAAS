"""Repository for source_connections table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class SourceConnectionRepository:
    """Data access for source_connections."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        params: dict = {}
        if source_type:
            conditions.append("source_type = :source_type")
            params["source_type"] = source_type
        if status:
            conditions.append("status = :status")
            params["status"] = status

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        count_sql = text(f"SELECT COUNT(*) FROM public.source_connections {where}")  # noqa: S608
        total = self._session.execute(count_sql, params).scalar() or 0

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        sql = text(f"""
            SELECT id, tenant_id, name, source_type, status, config_json,
                   credentials_ref, last_sync_at, created_by, created_at, updated_at
            FROM public.source_connections
            {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608
        rows = self._session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows], total

    def get(self, connection_id: int) -> dict | None:
        stmt = text("""
            SELECT id, tenant_id, name, source_type, status, config_json,
                   credentials_ref, last_sync_at, created_by, created_at, updated_at
            FROM public.source_connections
            WHERE id = :id
        """)
        row = self._session.execute(stmt, {"id": connection_id}).mappings().fetchone()
        return dict(row) if row else None

    # ── Write operations (Phase 1b) ──────────────────────────

    def create(
        self,
        *,
        tenant_id: int,
        name: str,
        source_type: str,
        config_json: dict,
        created_by: str | None = None,
    ) -> dict:
        """Insert a new source connection and return the inserted row."""
        stmt = text("""
            INSERT INTO public.source_connections
                (tenant_id, name, source_type, config_json, created_by)
            VALUES
                (:tenant_id, :name, :source_type, :config_json::jsonb, :created_by)
            RETURNING id, tenant_id, name, source_type, status, config_json,
                      credentials_ref, last_sync_at, created_by, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "name": name,
                    "source_type": source_type,
                    "config_json": json.dumps(config_json),
                    "created_by": created_by,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info(
            "source_connection_created",
            tenant_id=tenant_id,
            name=name,
            source_type=source_type,
        )
        return dict(row)

    def update(
        self,
        connection_id: int,
        *,
        name: str | None = None,
        status: str | None = None,
        config_json: dict | None = None,
        credentials_ref: str | None = None,
    ) -> dict | None:
        """Update specified fields. Returns the updated row or None if not found."""
        sets: list[str] = []
        params: dict = {"id": connection_id}
        if name is not None:
            sets.append("name = :name")
            params["name"] = name
        if status is not None:
            sets.append("status = :status")
            params["status"] = status
        if config_json is not None:
            sets.append("config_json = :config_json::jsonb")
            params["config_json"] = json.dumps(config_json)
        if credentials_ref is not None:
            sets.append("credentials_ref = :credentials_ref")
            params["credentials_ref"] = credentials_ref
        if not sets:
            # Nothing to update — return current state
            return self.get(connection_id)
        sets.append("updated_at = now()")
        stmt = text(f"""
            UPDATE public.source_connections
            SET {", ".join(sets)}
            WHERE id = :id
            RETURNING id, tenant_id, name, source_type, status, config_json,
                      credentials_ref, last_sync_at, created_by, created_at, updated_at
        """)  # noqa: S608
        row = self._session.execute(stmt, params).mappings().fetchone()
        return dict(row) if row else None

    def archive(self, connection_id: int) -> bool:
        """Set status to 'archived'. Returns True if a row was updated."""
        stmt = text("""
            UPDATE public.source_connections
            SET status = 'archived', updated_at = now()
            WHERE id = :id AND status != 'archived'
            RETURNING id
        """)
        row = self._session.execute(stmt, {"id": connection_id}).fetchone()
        return row is not None
