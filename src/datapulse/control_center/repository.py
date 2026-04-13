"""Repository layer for the Control Center.

All queries use SQLAlchemy text() with parameterized placeholders. RLS is
enforced by the caller's tenant-scoped session (SET LOCAL app.tenant_id).

Phase 1a: READ methods only.
Phase 1b: WRITE methods added to SourceConnectionRepository.
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
