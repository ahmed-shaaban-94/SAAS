"""Service layer for the Control Center — orchestrates repositories.

Phase 1a: READ-only.
Phase 1b: Connection CRUD + test + preview added.
Phase 1c: Profile / mapping CRUD + standalone mapping validation.
Phase 1d: Draft → validate → preview → publish → rollback workflow.
Phase 1e: Sync trigger (creates pipeline_runs + sync_jobs rows).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from datapulse.control_center import canonical as canonical_helpers
from datapulse.control_center.models import (
    CanonicalDomain,
    CanonicalDomainList,
    ConnectionPreviewResult,
    ConnectionTestResult,
    MappingTemplate,
    MappingTemplateList,
    PipelineDraft,
    PipelineDraftList,
    PipelineProfile,
    PipelineProfileList,
    PipelineRelease,
    PipelineReleaseList,
    SourceConnection,
    SourceConnectionList,
    SyncJob,
    SyncJobList,
    ValidationReport,
)
from datapulse.control_center.repository import (
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


# ── Connector registry ────────────────────────────────────────
# Lazy-imported to avoid pulling in file I/O dependencies at import time.


def _get_connector(source_type: str):  # type: ignore[return]
    """Return the connector instance for a given source_type, or None."""
    if source_type == "file_upload":
        from datapulse.control_center.connectors.file_upload import FileUploadConnector

        return FileUploadConnector()
    return None


class ControlCenterService:
    """Unified service facade — one object routes to the relevant repo."""

    def __init__(
        self,
        session: Session,
        *,
        connections: SourceConnectionRepository,
        profiles: PipelineProfileRepository,
        mappings: MappingTemplateRepository,
        releases: PipelineReleaseRepository,
        sync_jobs: SyncJobRepository,
        drafts: PipelineDraftRepository,
    ) -> None:
        self._session = session
        self._connections = connections
        self._profiles = profiles
        self._mappings = mappings
        self._releases = releases
        self._sync_jobs = sync_jobs
        self._drafts = drafts

    # ── Canonical domains ────────────────────────────────────

    def list_canonical_domains(self) -> CanonicalDomainList:
        rows = canonical_helpers.list_canonical_domains(self._session)
        return CanonicalDomainList(items=[CanonicalDomain(**r) for r in rows])

    # ── Source connections ───────────────────────────────────

    def list_connections(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SourceConnectionList:
        rows, total = self._connections.list(
            source_type=source_type, status=status, page=page, page_size=page_size
        )
        return SourceConnectionList(
            items=[SourceConnection(**r) for r in rows],
            total=total,
        )

    def get_connection(self, connection_id: int) -> SourceConnection | None:
        row = self._connections.get(connection_id)
        return SourceConnection(**row) if row else None

    # ── Connection writes (Phase 1b) ─────────────────────────

    def create_connection(
        self,
        *,
        tenant_id: int,
        name: str,
        source_type: str,
        config: dict,
        created_by: str | None = None,
    ) -> SourceConnection:
        """Create a new source connection for the current tenant."""
        row = self._connections.create(
            tenant_id=tenant_id,
            name=name,
            source_type=source_type,
            config_json=config,
            created_by=created_by,
        )
        return SourceConnection(**row)

    def update_connection(
        self,
        connection_id: int,
        *,
        name: str | None = None,
        status: str | None = None,
        config: dict | None = None,
    ) -> SourceConnection | None:
        """Update specified fields on an existing connection.

        Returns None when the connection is not found (or not accessible via RLS).
        """
        row = self._connections.update(
            connection_id,
            name=name,
            status=status,
            config_json=config,
        )
        return SourceConnection(**row) if row else None

    def archive_connection(self, connection_id: int) -> bool:
        """Set the connection status to 'archived'.

        Returns True if found, False if the id does not exist.
        """
        return self._connections.archive(connection_id)

    def test_connection(
        self,
        connection_id: int,
        *,
        tenant_id: int,
    ) -> ConnectionTestResult:
        """Run a connectivity test for the given source connection.

        Delegates to the appropriate SourceConnector.  Returns
        ``ok=False`` when the connection is not found or the source type
        has no connector registered yet.
        """
        conn = self.get_connection(connection_id)
        if conn is None:
            return ConnectionTestResult(ok=False, error="connection_not_found")

        connector = _get_connector(conn.source_type)
        if connector is None:
            return ConnectionTestResult(
                ok=False,
                error=f"test_not_supported_for_source_type:{conn.source_type}",
            )
        return connector.test(tenant_id=tenant_id, config=conn.config)

    def preview_connection(
        self,
        *,
        connection_id: int,
        tenant_id: int,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        """Return a read-only data sample for the given source connection.

        Raises:
            ValueError:        When the connection does not exist, or the
                               source type does not support preview.
            FileNotFoundError: When the underlying file is no longer available.
        """
        from datapulse.control_center import preview as preview_engine  # isolated module

        conn = self.get_connection(connection_id)
        if conn is None:
            raise ValueError("connection_not_found")

        if conn.source_type == "file_upload":
            return preview_engine.preview_file_upload(
                tenant_id,
                conn.config,
                max_rows=max_rows,
                sample_rows=sample_rows,
            )
        raise ValueError(f"preview_not_supported_for:{conn.source_type}")

    # ── Pipeline profiles ────────────────────────────────────

    def list_profiles(
        self,
        *,
        target_domain: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PipelineProfileList:
        rows, total = self._profiles.list(
            target_domain=target_domain, page=page, page_size=page_size
        )
        return PipelineProfileList(
            items=[PipelineProfile(**r) for r in rows],
            total=total,
        )

    def get_profile(self, profile_id: int) -> PipelineProfile | None:
        row = self._profiles.get(profile_id)
        return PipelineProfile(**row) if row else None

    # ── Profile writes (Phase 1c) ────────────────────────────

    def create_profile(
        self,
        *,
        tenant_id: int,
        profile_key: str,
        display_name: str,
        target_domain: str,
        is_default: bool = False,
        config: dict[str, Any],
    ) -> PipelineProfile:
        row = self._profiles.create(
            tenant_id=tenant_id,
            profile_key=profile_key,
            display_name=display_name,
            target_domain=target_domain,
            is_default=is_default,
            config_json=config,
        )
        return PipelineProfile(**row)

    def update_profile(
        self,
        profile_id: int,
        *,
        display_name: str | None = None,
        is_default: bool | None = None,
        config: dict[str, Any] | None = None,
    ) -> PipelineProfile | None:
        row = self._profiles.update(
            profile_id,
            display_name=display_name,
            is_default=is_default,
            config_json=config,
        )
        return PipelineProfile(**row) if row else None

    # ── Mapping templates ────────────────────────────────────

    def list_mappings(
        self,
        *,
        source_type: str | None = None,
        template_name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> MappingTemplateList:
        rows, total = self._mappings.list(
            source_type=source_type,
            template_name=template_name,
            page=page,
            page_size=page_size,
        )
        return MappingTemplateList(
            items=[MappingTemplate(**r) for r in rows],
            total=total,
        )

    def get_mapping(self, template_id: int) -> MappingTemplate | None:
        row = self._mappings.get(template_id)
        return MappingTemplate(**row) if row else None

    # ── Mapping writes (Phase 1c) ────────────────────────────

    def create_mapping(
        self,
        *,
        tenant_id: int,
        source_type: str,
        template_name: str,
        columns: list[dict[str, Any]],
        source_schema_hash: str | None = None,
        created_by: str | None = None,
    ) -> MappingTemplate:
        mapping_json = {"columns": columns}
        row = self._mappings.create(
            tenant_id=tenant_id,
            source_type=source_type,
            template_name=template_name,
            mapping_json=mapping_json,
            source_schema_hash=source_schema_hash,
            created_by=created_by,
        )
        return MappingTemplate(**row)

    def update_mapping(
        self,
        template_id: int,
        *,
        template_name: str | None = None,
        columns: list[dict[str, Any]] | None = None,
    ) -> MappingTemplate | None:
        mapping_json: dict[str, Any] | None = None
        if columns is not None:
            mapping_json = {"columns": columns}
        row = self._mappings.update(
            template_id,
            template_name=template_name,
            mapping_json=mapping_json,
        )
        return MappingTemplate(**row) if row else None

    def validate_mapping_standalone(
        self,
        *,
        columns: list[dict[str, Any]],
        target_domain: str,
        profile_config: dict[str, Any],
        source_preview: dict[str, Any] | None = None,
        tenant_id: int,
    ) -> ValidationReport:
        """Run the validation engine without persisting anything.

        Used by ``POST /mappings/validate`` for live feedback in the UI.
        """
        from datapulse.control_center import canonical as can_helpers  # noqa: PLC0415
        import datapulse.control_center.validation as val_engine  # noqa: PLC0415

        canonical = can_helpers.get_canonical_domain(self._session, target_domain)
        if canonical is None:
            from datapulse.control_center.models import ValidationIssue  # noqa: PLC0415

            return ValidationReport(
                ok=False,
                errors=[
                    ValidationIssue(
                        code="UNKNOWN_DOMAIN",
                        message=f"Canonical domain '{target_domain}' not found",
                        field="target_domain",
                    )
                ],
            )
        return val_engine.validate_draft(
            mapping_columns=columns,
            profile_config=profile_config,
            canonical_schema=canonical.get("json_schema", {}),
            source_preview=source_preview,
            tenant_id=tenant_id,
        )

    # ── Drafts (Phase 1d) ────────────────────────────────────

    def list_drafts(self, *, page: int = 1, page_size: int = 50) -> PipelineDraftList:
        rows, total = self._drafts.list(page=page, page_size=page_size)
        return PipelineDraftList(items=[PipelineDraft(**r) for r in rows], total=total)

    def get_draft(self, draft_id: int) -> PipelineDraft | None:
        row = self._drafts.get(draft_id)
        return PipelineDraft(**row) if row else None

    def create_draft(
        self,
        *,
        tenant_id: int,
        entity_type: str,
        entity_id: int | None = None,
        draft: dict[str, Any],
        created_by: str | None = None,
    ) -> PipelineDraft:
        row = self._drafts.create(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            draft_json=draft,
            created_by=created_by,
        )
        return PipelineDraft(**row)

    def validate_draft_workflow(
        self,
        draft_id: int,
        *,
        tenant_id: int,
    ) -> PipelineDraft:
        """Run validation engine on the draft and persist the report.

        Returns the updated draft. Raises ``ValueError`` when not found.
        """
        from datapulse.control_center import canonical as can_helpers  # noqa: PLC0415
        import datapulse.control_center.validation as val_engine  # noqa: PLC0415

        draft_row = self._drafts.get(draft_id)
        if draft_row is None:
            raise ValueError("draft_not_found")

        # Advance to 'validating'
        self._drafts.update_status(draft_id, "validating")

        draft_json: dict[str, Any] = draft_row.get("draft_json") or {}
        mapping_columns: list[dict[str, Any]] = draft_json.get("mapping_columns", [])
        profile_config: dict[str, Any] = draft_json.get("profile_config", {})
        target_domain: str = draft_json.get("target_domain", "")
        source_preview: dict[str, Any] | None = draft_json.get("source_preview")

        canonical = (
            can_helpers.get_canonical_domain(self._session, target_domain)
            if target_domain
            else None
        )
        canonical_schema = (canonical or {}).get("json_schema", {}) if canonical else {}

        prior_release = self._releases.latest()
        prior_snapshot: dict[str, Any] | None = (
            (prior_release or {}).get("snapshot_json") if prior_release else None
        )

        report = val_engine.validate_draft(
            mapping_columns=mapping_columns,
            profile_config=profile_config,
            canonical_schema=canonical_schema,
            source_preview=source_preview,
            prior_release_snapshot=prior_snapshot,
            tenant_id=tenant_id,
        )

        new_status = "validated" if report.ok else "invalidated"
        updated = self._drafts.update_validation(
            draft_id,
            status=new_status,
            validation_report_json=report.model_dump(),
        )
        if updated is None:
            raise RuntimeError("Failed to persist validation report")
        return PipelineDraft(**updated)

    def preview_draft(
        self,
        draft_id: int,
        *,
        tenant_id: int,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> PipelineDraft:
        """Run the preview engine on the draft's source connection.

        Returns the updated draft. Raises ``ValueError`` when not found or
        preview is not supported.
        """
        draft_row = self._drafts.get(draft_id)
        if draft_row is None:
            raise ValueError("draft_not_found")

        draft_json: dict[str, Any] = draft_row.get("draft_json") or {}
        connection_id: int | None = draft_json.get("source_connection_id")
        if connection_id is None:
            raise ValueError("draft_missing_source_connection_id")

        self._drafts.update_status(draft_id, "previewing")
        try:
            preview = self.preview_connection(
                connection_id=connection_id,
                tenant_id=tenant_id,
                max_rows=max_rows,
                sample_rows=sample_rows,
            )
            preview_dict = preview.model_dump()
            new_status = "previewed"
        except (ValueError, FileNotFoundError) as exc:
            preview_dict = {"error": str(exc)}
            new_status = "preview_failed"

        updated = self._drafts.update_preview(
            draft_id,
            status=new_status,
            preview_result_json=preview_dict,
        )
        if updated is None:
            raise RuntimeError("Failed to persist preview result")
        return PipelineDraft(**updated)

    def publish_draft(
        self,
        draft_id: int,
        *,
        tenant_id: int,
        release_notes: str = "",
        published_by: str | None = None,
    ) -> PipelineRelease:
        """Atomically publish a validated draft as a new release.

        Steps:
         1. Verify draft exists and is in a publishable state.
         2. Snapshot: gather connection + profile + mapping into snapshot_json.
         3. Insert into pipeline_releases (append-only).
         4. Mark draft as 'published'.
         5. Invalidate analytics cache for the tenant.

        Returns the newly created ``PipelineRelease``.
        Raises ``ValueError`` on invalid state.
        """
        draft_row = self._drafts.get(draft_id)
        if draft_row is None:
            raise ValueError("draft_not_found")

        allowed_statuses = {"validated", "previewed"}
        if draft_row.get("status") not in allowed_statuses:
            raise ValueError(
                f"draft_not_publishable: status is '{draft_row.get('status')}', "
                f"expected one of {allowed_statuses}"
            )

        # Mark publishing in progress
        self._drafts.update_status(draft_id, "publishing")

        # Build snapshot from draft_json
        draft_json: dict[str, Any] = draft_row.get("draft_json") or {}
        snapshot: dict[str, Any] = {
            "draft_id": draft_id,
            "draft_json": draft_json,
            "published_at": datetime.now(UTC).isoformat(),
            "tenant_id": tenant_id,
        }

        # Optionally embed referenced entities for full snapshot fidelity
        conn_id: int | None = draft_json.get("source_connection_id")
        if conn_id is not None:
            conn_row = self._connections.get(conn_id)
            if conn_row:
                snapshot["source_connection"] = conn_row

        profile_id: int | None = draft_json.get("profile_id")
        if profile_id is not None:
            profile_row = self._profiles.get(profile_id)
            if profile_row:
                snapshot["pipeline_profile"] = profile_row

        mapping_id: int | None = draft_json.get("mapping_template_id")
        if mapping_id is not None:
            mapping_row = self._mappings.get(mapping_id)
            if mapping_row:
                snapshot["mapping_template"] = mapping_row

        try:
            release_row = self._releases.create(
                tenant_id=tenant_id,
                draft_id=draft_id,
                snapshot_json=snapshot,
                release_notes=release_notes,
                is_rollback=False,
                published_by=published_by,
            )
        except Exception:
            self._drafts.update_status(draft_id, "publish_failed")
            raise

        self._drafts.update_status(draft_id, "published")

        # Invalidate analytics cache for this tenant
        try:
            from datapulse.cache import cache_invalidate_pattern  # noqa: PLC0415

            cache_invalidate_pattern(f"datapulse:analytics:{tenant_id}:*")
        except Exception:  # noqa: BLE001
            log.warning("cache_invalidation_failed_after_publish", tenant_id=tenant_id)

        log.info(
            "control_center.release.published",
            tenant_id=tenant_id,
            release_id=release_row["id"],
            release_version=release_row["release_version"],
            draft_id=draft_id,
        )
        return PipelineRelease(**release_row)

    def rollback_release(
        self,
        release_id: int,
        *,
        tenant_id: int,
        published_by: str | None = None,
    ) -> PipelineRelease:
        """Create a new release whose snapshot equals the target release.

        Rollback is append-only — it never mutates or deletes the existing row.
        Returns the NEW release created by the rollback.
        Raises ``ValueError`` when the target release is not found.
        """
        target = self._releases.get(release_id)
        if target is None:
            raise ValueError("release_not_found")

        rollback_snapshot: dict[str, Any] = {
            **(target.get("snapshot_json") or {}),
            "rollback_source_release_id": release_id,
            "rollback_at": datetime.now(UTC).isoformat(),
        }

        new_release_row = self._releases.create(
            tenant_id=tenant_id,
            source_release_id=release_id,
            snapshot_json=rollback_snapshot,
            release_notes=f"Rollback to release {target.get('release_version')}",
            is_rollback=True,
            published_by=published_by,
        )

        # Invalidate analytics cache
        try:
            from datapulse.cache import cache_invalidate_pattern  # noqa: PLC0415

            cache_invalidate_pattern(f"datapulse:analytics:{tenant_id}:*")
        except Exception:  # noqa: BLE001
            log.warning("cache_invalidation_failed_after_rollback", tenant_id=tenant_id)

        log.info(
            "control_center.release.rolled_back",
            tenant_id=tenant_id,
            source_release_id=release_id,
            new_release_id=new_release_row["id"],
        )
        return PipelineRelease(**new_release_row)

    # ── Releases ─────────────────────────────────────────────

    def list_releases(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> PipelineReleaseList:
        rows, total = self._releases.list(page=page, page_size=page_size)
        return PipelineReleaseList(
            items=[PipelineRelease(**r) for r in rows],
            total=total,
        )

    def get_release(self, release_id: int) -> PipelineRelease | None:
        row = self._releases.get(release_id)
        return PipelineRelease(**row) if row else None

    # ── Sync (Phase 1e) ──────────────────────────────────────

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
        conn = self.get_connection(connection_id)
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

    # ── Sync history ─────────────────────────────────────────

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
