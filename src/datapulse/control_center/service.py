"""ControlCenterService — thin facade that delegates to domain sub-services.

Public API is identical to the original monolithic service. All imports of
``from datapulse.control_center.service import ControlCenterService`` continue
to work without modification.

Domain sub-services:
- SourcesService  : connection CRUD, connectivity test, preview, canonical domains
- PipelinesService: profiles, drafts, releases (validate / publish / rollback)
- MappingsService : mapping templates + standalone validation
- SyncService     : sync-job execution, history, schedules, health summary
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from datapulse.control_center.models import (
    CanonicalDomainList,
    ConnectionPreviewResult,
    ConnectionTestResult,
    HealthSummary,
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
    SyncSchedule,
    SyncScheduleList,
    ValidationReport,
)
from datapulse.control_center.repository import (
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
    SyncScheduleRepository,
)
from datapulse.control_center.services.mappings import MappingsService
from datapulse.control_center.services.pipelines import PipelinesService
from datapulse.control_center.services.sources import SourcesService
from datapulse.control_center.services.sync import SyncService


class ControlCenterService:
    """Unified service facade — delegates to per-domain sub-services."""

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
        schedules: SyncScheduleRepository,
    ) -> None:
        self._session = session

        # Instantiate domain sub-services
        self._sources = SourcesService(session=session, connections=connections)
        self._mappings_svc = MappingsService(session=session, mappings=mappings)
        self._sync = SyncService(
            session=session,
            connections=connections,
            sync_jobs=sync_jobs,
            schedules=schedules,
            releases=releases,
        )
        self._pipelines = PipelinesService(
            session=session,
            connections=connections,
            profiles=profiles,
            mappings=mappings,
            releases=releases,
            drafts=drafts,
            preview_connection=self._sources.preview_connection,
        )

    # ── Canonical domains ────────────────────────────────────────────────────

    def list_canonical_domains(self) -> CanonicalDomainList:
        return self._sources.list_canonical_domains()

    # ── Source connections ───────────────────────────────────────────────────

    def list_connections(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SourceConnectionList:
        return self._sources.list_connections(
            source_type=source_type, status=status, page=page, page_size=page_size
        )

    def get_connection(self, connection_id: int) -> SourceConnection | None:
        return self._sources.get_connection(connection_id)

    def create_connection(
        self,
        *,
        tenant_id: int,
        name: str,
        source_type: str,
        config: dict,
        created_by: str | None = None,
    ) -> SourceConnection:
        return self._sources.create_connection(
            tenant_id=tenant_id,
            name=name,
            source_type=source_type,
            config=config,
            created_by=created_by,
        )

    def update_connection(
        self,
        connection_id: int,
        *,
        tenant_id: int,
        name: str | None = None,
        status: str | None = None,
        config: dict | None = None,
        credential: str | None = None,
    ) -> SourceConnection | None:
        return self._sources.update_connection(
            connection_id,
            tenant_id=tenant_id,
            name=name,
            status=status,
            config=config,
            credential=credential,
        )

    def archive_connection(self, connection_id: int) -> bool:
        return self._sources.archive_connection(connection_id)

    def test_connection(
        self,
        connection_id: int,
        *,
        tenant_id: int,
    ) -> ConnectionTestResult:
        return self._sources.test_connection(connection_id, tenant_id=tenant_id)

    def preview_connection(
        self,
        *,
        connection_id: int,
        tenant_id: int,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        return self._sources.preview_connection(
            connection_id=connection_id,
            tenant_id=tenant_id,
            max_rows=max_rows,
            sample_rows=sample_rows,
        )

    # ── Pipeline profiles ────────────────────────────────────────────────────

    def list_profiles(
        self,
        *,
        target_domain: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PipelineProfileList:
        return self._pipelines.list_profiles(
            target_domain=target_domain, page=page, page_size=page_size
        )

    def get_profile(self, profile_id: int) -> PipelineProfile | None:
        return self._pipelines.get_profile(profile_id)

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
        return self._pipelines.create_profile(
            tenant_id=tenant_id,
            profile_key=profile_key,
            display_name=display_name,
            target_domain=target_domain,
            is_default=is_default,
            config=config,
        )

    def update_profile(
        self,
        profile_id: int,
        *,
        display_name: str | None = None,
        is_default: bool | None = None,
        config: dict[str, Any] | None = None,
    ) -> PipelineProfile | None:
        return self._pipelines.update_profile(
            profile_id,
            display_name=display_name,
            is_default=is_default,
            config=config,
        )

    # ── Mapping templates ────────────────────────────────────────────────────

    def list_mappings(
        self,
        *,
        source_type: str | None = None,
        template_name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> MappingTemplateList:
        return self._mappings_svc.list_mappings(
            source_type=source_type,
            template_name=template_name,
            page=page,
            page_size=page_size,
        )

    def get_mapping(self, template_id: int) -> MappingTemplate | None:
        return self._mappings_svc.get_mapping(template_id)

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
        return self._mappings_svc.create_mapping(
            tenant_id=tenant_id,
            source_type=source_type,
            template_name=template_name,
            columns=columns,
            source_schema_hash=source_schema_hash,
            created_by=created_by,
        )

    def update_mapping(
        self,
        template_id: int,
        *,
        template_name: str | None = None,
        columns: list[dict[str, Any]] | None = None,
    ) -> MappingTemplate | None:
        return self._mappings_svc.update_mapping(
            template_id,
            template_name=template_name,
            columns=columns,
        )

    def validate_mapping_standalone(
        self,
        *,
        columns: list[dict[str, Any]],
        target_domain: str,
        profile_config: dict[str, Any],
        source_preview: dict[str, Any] | None = None,
        tenant_id: int,
    ) -> ValidationReport:
        return self._mappings_svc.validate_mapping_standalone(
            columns=columns,
            target_domain=target_domain,
            profile_config=profile_config,
            source_preview=source_preview,
            tenant_id=tenant_id,
        )

    # ── Drafts ───────────────────────────────────────────────────────────────

    def list_drafts(self, *, page: int = 1, page_size: int = 50) -> PipelineDraftList:
        return self._pipelines.list_drafts(page=page, page_size=page_size)

    def get_draft(self, draft_id: int) -> PipelineDraft | None:
        return self._pipelines.get_draft(draft_id)

    def create_draft(
        self,
        *,
        tenant_id: int,
        entity_type: str,
        entity_id: int | None = None,
        draft: dict[str, Any],
        created_by: str | None = None,
    ) -> PipelineDraft:
        return self._pipelines.create_draft(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            draft=draft,
            created_by=created_by,
        )

    def validate_draft_workflow(
        self,
        draft_id: int,
        *,
        tenant_id: int,
    ) -> PipelineDraft:
        return self._pipelines.validate_draft_workflow(draft_id, tenant_id=tenant_id)

    def preview_draft(
        self,
        draft_id: int,
        *,
        tenant_id: int,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> PipelineDraft:
        return self._pipelines.preview_draft(
            draft_id,
            tenant_id=tenant_id,
            max_rows=max_rows,
            sample_rows=sample_rows,
        )

    def publish_draft(
        self,
        draft_id: int,
        *,
        tenant_id: int,
        release_notes: str = "",
        published_by: str | None = None,
    ) -> PipelineRelease:
        return self._pipelines.publish_draft(
            draft_id,
            tenant_id=tenant_id,
            release_notes=release_notes,
            published_by=published_by,
        )

    def rollback_release(
        self,
        release_id: int,
        *,
        tenant_id: int,
        published_by: str | None = None,
    ) -> PipelineRelease:
        return self._pipelines.rollback_release(
            release_id,
            tenant_id=tenant_id,
            published_by=published_by,
        )

    # ── Releases ─────────────────────────────────────────────────────────────

    def list_releases(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> PipelineReleaseList:
        return self._pipelines.list_releases(page=page, page_size=page_size)

    def get_release(self, release_id: int) -> PipelineRelease | None:
        return self._pipelines.get_release(release_id)

    # ── Sync ─────────────────────────────────────────────────────────────────

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
        return self._sync.trigger_sync(
            connection_id,
            tenant_id=tenant_id,
            run_mode=run_mode,
            release_id=release_id,
            profile_id=profile_id,
            created_by=created_by,
        )

    def list_sync_history(
        self,
        *,
        connection_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> SyncJobList:
        return self._sync.list_sync_history(
            connection_id=connection_id, page=page, page_size=page_size
        )

    # ── Sync schedules ───────────────────────────────────────────────────────

    def create_schedule(
        self,
        *,
        connection_id: int,
        tenant_id: int,
        cron_expr: str,
        is_active: bool = True,
        created_by: str | None = None,
    ) -> SyncSchedule:
        return self._sync.create_schedule(
            connection_id=connection_id,
            tenant_id=tenant_id,
            cron_expr=cron_expr,
            is_active=is_active,
            created_by=created_by,
        )

    def list_schedules(
        self,
        *,
        connection_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> SyncScheduleList:
        return self._sync.list_schedules(
            connection_id=connection_id, page=page, page_size=page_size
        )

    def delete_schedule(self, schedule_id: int) -> bool:
        return self._sync.delete_schedule(schedule_id)

    # ── Health summary ───────────────────────────────────────────────────────

    def get_health_summary(self, *, tenant_id: int) -> HealthSummary:
        return self._sync.get_health_summary(tenant_id=tenant_id)
