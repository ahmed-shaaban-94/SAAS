"""Repository for pipeline_profiles table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class PipelineProfileRepository:
    """Data access for pipeline_profiles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        target_domain: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        params: dict = {}
        if target_domain:
            conditions.append("target_domain = :target_domain")
            params["target_domain"] = target_domain

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        count_sql = text(f"SELECT COUNT(*) FROM public.pipeline_profiles {where}")  # noqa: S608
        total = self._session.execute(count_sql, params).scalar() or 0

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        sql = text(f"""
            SELECT id, tenant_id, profile_key, display_name, target_domain,
                   is_default, config_json, created_at, updated_at
            FROM public.pipeline_profiles
            {where}
            ORDER BY is_default DESC, profile_key
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608
        rows = self._session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows], total

    def get(self, profile_id: int) -> dict | None:
        stmt = text("""
            SELECT id, tenant_id, profile_key, display_name, target_domain,
                   is_default, config_json, created_at, updated_at
            FROM public.pipeline_profiles
            WHERE id = :id
        """)
        row = self._session.execute(stmt, {"id": profile_id}).mappings().fetchone()
        return dict(row) if row else None

    # ── Write operations (Phase 1c) ──────────────────────────

    def create(
        self,
        *,
        tenant_id: int,
        profile_key: str,
        display_name: str,
        target_domain: str,
        is_default: bool = False,
        config_json: dict,
    ) -> dict:
        """Insert a new pipeline profile and return the inserted row."""
        stmt = text("""
            INSERT INTO public.pipeline_profiles
                (tenant_id, profile_key, display_name, target_domain,
                 is_default, config_json)
            VALUES
                (:tenant_id, :profile_key, :display_name, :target_domain,
                 :is_default, :config_json::jsonb)
            RETURNING id, tenant_id, profile_key, display_name, target_domain,
                      is_default, config_json, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "profile_key": profile_key,
                    "display_name": display_name,
                    "target_domain": target_domain,
                    "is_default": is_default,
                    "config_json": json.dumps(config_json),
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING unexpectedly returned no row")
        log.info("pipeline_profile_created", tenant_id=tenant_id, profile_key=profile_key)
        return dict(row)

    def update(
        self,
        profile_id: int,
        *,
        display_name: str | None = None,
        is_default: bool | None = None,
        config_json: dict | None = None,
    ) -> dict | None:
        """Update specified fields. Returns the updated row or None if not found."""
        sets: list[str] = []
        params: dict = {"id": profile_id}
        if display_name is not None:
            sets.append("display_name = :display_name")
            params["display_name"] = display_name
        if is_default is not None:
            sets.append("is_default = :is_default")
            params["is_default"] = is_default
        if config_json is not None:
            sets.append("config_json = :config_json::jsonb")
            params["config_json"] = json.dumps(config_json)
        if not sets:
            return self.get(profile_id)
        sets.append("updated_at = now()")
        stmt = text(f"""
            UPDATE public.pipeline_profiles
            SET {", ".join(sets)}
            WHERE id = :id
            RETURNING id, tenant_id, profile_key, display_name, target_domain,
                      is_default, config_json, created_at, updated_at
        """)  # noqa: S608
        row = self._session.execute(stmt, params).mappings().fetchone()
        return dict(row) if row else None
