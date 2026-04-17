"""PipelinesService — pipeline profiles, drafts, and release lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from datapulse.control_center.models import (
    ConnectionPreviewResult,
    PipelineDraft,
    PipelineDraftList,
    PipelineProfile,
    PipelineProfileList,
    PipelineRelease,
    PipelineReleaseList,
)
from datapulse.control_center.repository import (
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class PipelinesService:
    """Pipeline profile / draft / release lifecycle management."""

    def __init__(
        self,
        session: Session,
        *,
        connections: SourceConnectionRepository,
        profiles: PipelineProfileRepository,
        mappings: MappingTemplateRepository,
        releases: PipelineReleaseRepository,
        drafts: PipelineDraftRepository,
        preview_connection: Callable[..., ConnectionPreviewResult],
    ) -> None:
        self._session = session
        self._connections = connections
        self._profiles = profiles
        self._mappings = mappings
        self._releases = releases
        self._drafts = drafts
        self._preview_connection = preview_connection

    # ── Pipeline profiles ────────────────────────────────────────────────────

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

    # ── Drafts ───────────────────────────────────────────────────────────────

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
        import datapulse.control_center.validation as val_engine  # noqa: PLC0415
        from datapulse.control_center import canonical as can_helpers  # noqa: PLC0415

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
            preview = self._preview_connection(
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

        # Complete onboarding step on the tenant's very first release
        if self._releases.count_for_tenant(tenant_id) == 1:
            try:
                from datapulse.onboarding.repository import OnboardingRepository  # noqa: PLC0415
                from datapulse.onboarding.service import OnboardingService  # noqa: PLC0415

                onboarding_svc = OnboardingService(OnboardingRepository(self._session))
                onboarding_svc.complete_step(
                    tenant_id=tenant_id,
                    user_id=published_by or "system",
                    step="configure_first_profile",
                )
            except ValueError:
                pass  # step already completed — no-op

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

    # ── Releases ─────────────────────────────────────────────────────────────

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
