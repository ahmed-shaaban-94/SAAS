"""Control Center API — unified data control plane.

Phase 1a: READ-only endpoints.
Phase 1b: Connection CRUD + test + preview (file_upload sources).
Writes (drafts, publish, rollback, sync) land in Phase 1c–1e.
Phase 2: Schedule CRUD endpoints (POST/GET/DELETE /connections/{id}/schedule*).

All endpoints are gated by:
  - Auth: Auth0 / API key via get_current_user
  - Tenant scope: get_tenant_session sets app.tenant_id for RLS
  - RBAC: require_permission("control_center:*")
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.control_center.models import (
    CanonicalDomainList,
    ConnectionPreviewResult,
    ConnectionTestResult,
    CreateConnectionRequest,
    CreateDraftRequest,
    CreateMappingRequest,
    CreateProfileRequest,
    CreateScheduleRequest,
    MappingTemplate,
    MappingTemplateList,
    PipelineDraft,
    PipelineDraftList,
    PipelineProfile,
    PipelineProfileList,
    PipelineRelease,
    PipelineReleaseList,
    PublishDraftRequest,
    SourceConnection,
    SourceConnectionList,
    SyncJob,
    SyncJobList,
    SyncSchedule,
    SyncScheduleList,
    TriggerSyncRequest,
    UpdateConnectionRequest,
    UpdateMappingRequest,
    UpdateProfileRequest,
    ValidateMappingRequest,
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
from datapulse.control_center.service import ControlCenterService
from datapulse.rbac.dependencies import require_permission

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter(
    prefix="/control-center",
    tags=["control-center"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Dependency injection — local factory (follows onboarding pattern)
# ------------------------------------------------------------------


def get_control_center_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ControlCenterService:
    return ControlCenterService(
        session,
        connections=SourceConnectionRepository(session),
        profiles=PipelineProfileRepository(session),
        mappings=MappingTemplateRepository(session),
        releases=PipelineReleaseRepository(session),
        sync_jobs=SyncJobRepository(session),
        drafts=PipelineDraftRepository(session),
        schedules=SyncScheduleRepository(session),
    )


ServiceDep = Annotated[ControlCenterService, Depends(get_control_center_service)]


# ------------------------------------------------------------------
# Canonical domains — public read (all authenticated users)
# ------------------------------------------------------------------


@router.get("/canonical-domains", response_model=CanonicalDomainList)
@limiter.limit("60/minute")
def list_canonical_domains(
    request: Request,
    service: ServiceDep,
) -> CanonicalDomainList:
    """List all active canonical semantic domains."""
    return service.list_canonical_domains()


# ------------------------------------------------------------------
# Source connections — view
# ------------------------------------------------------------------


@router.get(
    "/connections",
    response_model=SourceConnectionList,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def list_connections(
    request: Request,
    service: ServiceDep,
    source_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SourceConnectionList:
    """List registered data sources for the current tenant."""
    return service.list_connections(
        source_type=source_type, status=status, page=page, page_size=page_size
    )


@router.get(
    "/connections/{connection_id}",
    response_model=SourceConnection,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def get_connection(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
) -> SourceConnection:
    """Fetch one source connection by id."""
    conn = service.get_connection(connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return conn


# ------------------------------------------------------------------
# Source connections — write (Phase 1b)
# ------------------------------------------------------------------


@router.post(
    "/connections",
    response_model=SourceConnection,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:connections:manage"))],
)
@limiter.limit("30/minute")
def create_connection(
    request: Request,
    service: ServiceDep,
    body: CreateConnectionRequest,
    user: UserDep,
) -> SourceConnection:
    """Register a new source connection for the current tenant.

    Phase 1b supports ``source_type=file_upload`` only.  The ``config``
    object must include ``file_id`` (UUID from /upload/files) and
    ``filename`` (original file name including extension).
    """
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    return service.create_connection(
        tenant_id=tenant_id,
        name=body.name,
        source_type=body.source_type,
        config=body.config,
        created_by=created_by,
    )


@router.patch(
    "/connections/{connection_id}",
    response_model=SourceConnection,
    dependencies=[Depends(require_permission("control_center:connections:manage"))],
)
@limiter.limit("30/minute")
def update_connection(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    body: UpdateConnectionRequest,
    user: UserDep,
) -> SourceConnection:
    """Update one or more fields on an existing source connection.

    Only the fields present in the request body are updated (partial update).

    The optional ``credential`` field (write-only) is encrypted at rest via
    pgcrypto and NEVER returned in the response.  Requires
    CONTROL_CENTER_CREDS_KEY to be set in the environment.
    """
    tenant_id = int(user.get("tenant_id", 1))
    conn = service.update_connection(
        connection_id,
        tenant_id=tenant_id,
        name=body.name,
        status=body.status,
        config=body.config,
        credential=body.credential,
    )
    if conn is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return conn


@router.delete(
    "/connections/{connection_id}",
    status_code=204,
    dependencies=[Depends(require_permission("control_center:connections:manage"))],
)
@limiter.limit("30/minute")
def archive_connection(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
) -> None:
    """Archive a source connection (sets status to 'archived').

    The row is retained for audit purposes. Use PATCH to restore it.
    """
    found = service.archive_connection(connection_id)
    if not found:
        raise HTTPException(status_code=404, detail="connection_not_found")


@router.post(
    "/connections/{connection_id}/test",
    response_model=ConnectionTestResult,
    dependencies=[Depends(require_permission("control_center:connections:manage"))],
)
@limiter.limit("20/minute")
def test_connection(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    connection_id: Annotated[int, Path(ge=1)],
) -> ConnectionTestResult:
    """Verify that the source connection is reachable.

    For ``file_upload`` sources, this checks whether the uploaded file
    is still present in the temp directory.
    """
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    tenant_id = int(user.get("tenant_id", 1))
    return service.test_connection(connection_id, tenant_id=tenant_id)


@router.post(
    "/connections/{connection_id}/preview",
    response_model=ConnectionPreviewResult,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("10/minute")
def preview_connection(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    connection_id: Annotated[int, Path(ge=1)],
    max_rows: Annotated[int, Query(ge=1, le=10_000)] = 1000,
    sample_rows: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ConnectionPreviewResult:
    """Return a read-only data sample for the source connection.

    Reads the uploaded file directly — never writes to bronze.
    ``max_rows`` caps total rows read; ``sample_rows`` caps rows in the response.
    """
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    tenant_id = int(user.get("tenant_id", 1))
    try:
        return service.preview_connection(
            connection_id=connection_id,
            tenant_id=tenant_id,
            max_rows=max_rows,
            sample_rows=sample_rows,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Pipeline profiles — view
# ------------------------------------------------------------------


@router.get(
    "/profiles",
    response_model=PipelineProfileList,
    dependencies=[Depends(require_permission("control_center:profiles:view"))],
)
@limiter.limit("60/minute")
def list_profiles(
    request: Request,
    service: ServiceDep,
    target_domain: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PipelineProfileList:
    """List pipeline profiles for the current tenant."""
    return service.list_profiles(target_domain=target_domain, page=page, page_size=page_size)


@router.get(
    "/profiles/{profile_id}",
    response_model=PipelineProfile,
    dependencies=[Depends(require_permission("control_center:profiles:view"))],
)
@limiter.limit("60/minute")
def get_profile(
    request: Request,
    service: ServiceDep,
    profile_id: Annotated[int, Path(ge=1)],
) -> PipelineProfile:
    """Fetch one pipeline profile by id."""
    profile = service.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return profile


# ------------------------------------------------------------------
# Mapping templates — editor+ (view via mappings:manage; tighter than others
# because mappings reveal column-level business logic)
# ------------------------------------------------------------------


@router.get(
    "/mappings",
    response_model=MappingTemplateList,
    dependencies=[Depends(require_permission("control_center:mappings:manage"))],
)
@limiter.limit("60/minute")
def list_mappings(
    request: Request,
    service: ServiceDep,
    source_type: Annotated[str | None, Query()] = None,
    template_name: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> MappingTemplateList:
    """List mapping templates for the current tenant."""
    return service.list_mappings(
        source_type=source_type,
        template_name=template_name,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/mappings/{template_id}",
    response_model=MappingTemplate,
    dependencies=[Depends(require_permission("control_center:mappings:manage"))],
)
@limiter.limit("60/minute")
def get_mapping(
    request: Request,
    service: ServiceDep,
    template_id: Annotated[int, Path(ge=1)],
) -> MappingTemplate:
    """Fetch one mapping template by id."""
    tpl = service.get_mapping(template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="mapping_template_not_found")
    return tpl


# ------------------------------------------------------------------
# Releases — view (admin only; uses profiles:view as the baseline guard
# since releases contain config snapshots)
# ------------------------------------------------------------------


@router.get(
    "/releases",
    response_model=PipelineReleaseList,
    dependencies=[Depends(require_permission("control_center:profiles:view"))],
)
@limiter.limit("60/minute")
def list_releases(
    request: Request,
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PipelineReleaseList:
    """List published releases (append-only, newest first)."""
    return service.list_releases(page=page, page_size=page_size)


@router.get(
    "/releases/{release_id}",
    response_model=PipelineRelease,
    dependencies=[Depends(require_permission("control_center:profiles:view"))],
)
@limiter.limit("60/minute")
def get_release(
    request: Request,
    service: ServiceDep,
    release_id: Annotated[int, Path(ge=1)],
) -> PipelineRelease:
    """Fetch one release by id — includes full snapshot_json."""
    rel = service.get_release(release_id)
    if rel is None:
        raise HTTPException(status_code=404, detail="release_not_found")
    return rel


# ------------------------------------------------------------------
# Sync history — view (connection-scoped)
# ------------------------------------------------------------------


@router.get(
    "/connections/{connection_id}/sync-history",
    response_model=SyncJobList,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def list_sync_history(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SyncJobList:
    """List past sync jobs for a source connection (joined with pipeline_runs)."""
    # Verify connection exists & is tenant-visible (RLS enforces scope)
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return service.list_sync_history(connection_id=connection_id, page=page, page_size=page_size)


# ------------------------------------------------------------------
# Pipeline profiles — write (Phase 1c)
# ------------------------------------------------------------------


@router.post(
    "/profiles",
    response_model=PipelineProfile,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:profiles:manage"))],
)
@limiter.limit("30/minute")
def create_profile(
    request: Request,
    service: ServiceDep,
    body: CreateProfileRequest,
    user: UserDep,
) -> PipelineProfile:
    """Create a new pipeline profile targeting a canonical domain."""
    tenant_id = int(user.get("tenant_id", 1))
    return service.create_profile(
        tenant_id=tenant_id,
        profile_key=body.profile_key,
        display_name=body.display_name,
        target_domain=body.target_domain,
        is_default=body.is_default,
        config=body.config,
    )


@router.patch(
    "/profiles/{profile_id}",
    response_model=PipelineProfile,
    dependencies=[Depends(require_permission("control_center:profiles:manage"))],
)
@limiter.limit("30/minute")
def update_profile(
    request: Request,
    service: ServiceDep,
    profile_id: Annotated[int, Path(ge=1)],
    body: UpdateProfileRequest,
) -> PipelineProfile:
    """Update one or more fields on an existing pipeline profile."""
    profile = service.update_profile(
        profile_id,
        display_name=body.display_name,
        is_default=body.is_default,
        config=body.config,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return profile


# ------------------------------------------------------------------
# Mapping templates — write (Phase 1c)
# ------------------------------------------------------------------


@router.post(
    "/mappings",
    response_model=MappingTemplate,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:mappings:manage"))],
)
@limiter.limit("30/minute")
def create_mapping(
    request: Request,
    service: ServiceDep,
    body: CreateMappingRequest,
    user: UserDep,
) -> MappingTemplate:
    """Create a new column-mapping template."""
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    return service.create_mapping(
        tenant_id=tenant_id,
        source_type=body.source_type,
        template_name=body.template_name,
        columns=body.columns,
        source_schema_hash=body.source_schema_hash,
        created_by=created_by,
    )


@router.patch(
    "/mappings/{template_id}",
    response_model=MappingTemplate,
    dependencies=[Depends(require_permission("control_center:mappings:manage"))],
)
@limiter.limit("30/minute")
def update_mapping(
    request: Request,
    service: ServiceDep,
    template_id: Annotated[int, Path(ge=1)],
    body: UpdateMappingRequest,
) -> MappingTemplate:
    """Update a mapping template; automatically bumps the version counter."""
    tpl = service.update_mapping(
        template_id,
        template_name=body.template_name,
        columns=body.columns,
    )
    if tpl is None:
        raise HTTPException(status_code=404, detail="mapping_template_not_found")
    return tpl


@router.post(
    "/mappings/validate",
    response_model=ValidationReport,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("20/minute")
def validate_mapping(
    request: Request,
    service: ServiceDep,
    body: ValidateMappingRequest,
    user: UserDep,
) -> ValidationReport:
    """Validate a mapping against its target canonical domain — no persistence.

    Useful for live feedback in the mapping editor before saving.
    """
    tenant_id = int(user.get("tenant_id", 1))
    return service.validate_mapping_standalone(
        columns=body.columns,
        target_domain=body.target_domain,
        profile_config=body.profile_config,
        source_preview=body.source_preview,
        tenant_id=tenant_id,
    )


# ------------------------------------------------------------------
# Drafts — workflow (Phase 1d)
# ------------------------------------------------------------------


@router.get(
    "/drafts",
    response_model=PipelineDraftList,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("60/minute")
def list_drafts(
    request: Request,
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PipelineDraftList:
    """List pipeline drafts for the current tenant."""
    return service.list_drafts(page=page, page_size=page_size)


@router.post(
    "/drafts",
    response_model=PipelineDraft,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("20/minute")
def create_draft(
    request: Request,
    service: ServiceDep,
    body: CreateDraftRequest,
    user: UserDep,
) -> PipelineDraft:
    """Create a new pipeline draft (entity bundle to be published)."""
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    return service.create_draft(
        tenant_id=tenant_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        draft=body.draft,
        created_by=created_by,
    )


@router.get(
    "/drafts/{draft_id}",
    response_model=PipelineDraft,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("60/minute")
def get_draft(
    request: Request,
    service: ServiceDep,
    draft_id: Annotated[int, Path(ge=1)],
) -> PipelineDraft:
    """Fetch one draft by id — includes validation report and preview result."""
    draft = service.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="draft_not_found")
    return draft


@router.post(
    "/drafts/{draft_id}/validate",
    response_model=PipelineDraft,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("10/minute")
def validate_draft(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    draft_id: Annotated[int, Path(ge=1)],
) -> PipelineDraft:
    """Run the validation engine on the draft and persist the report."""
    tenant_id = int(user.get("tenant_id", 1))
    try:
        return service.validate_draft_workflow(draft_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/drafts/{draft_id}/preview",
    response_model=PipelineDraft,
    dependencies=[Depends(require_permission("control_center:pipeline:preview"))],
)
@limiter.limit("5/minute")
def preview_draft(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    draft_id: Annotated[int, Path(ge=1)],
    max_rows: Annotated[int, Query(ge=1, le=10_000)] = 1000,
    sample_rows: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PipelineDraft:
    """Run the preview engine on the draft's source connection."""
    tenant_id = int(user.get("tenant_id", 1))
    try:
        return service.preview_draft(
            draft_id,
            tenant_id=tenant_id,
            max_rows=max_rows,
            sample_rows=sample_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/drafts/{draft_id}/publish",
    response_model=PipelineRelease,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:pipeline:publish"))],
)
@limiter.limit("5/minute")
def publish_draft(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    draft_id: Annotated[int, Path(ge=1)],
    body: PublishDraftRequest,
) -> PipelineRelease:
    """Publish a validated draft as an immutable release snapshot.

    Atomically:
    1. Captures a full snapshot of the source connection, profile, and mapping.
    2. Inserts into ``pipeline_releases`` (append-only).
    3. Marks the draft terminal (``published``).
    4. Invalidates the tenant's analytics cache.
    """
    tenant_id = int(user.get("tenant_id", 1))
    published_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    try:
        return service.publish_draft(
            draft_id,
            tenant_id=tenant_id,
            release_notes=body.release_notes,
            published_by=published_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Releases — rollback (Phase 1d)
# ------------------------------------------------------------------


@router.post(
    "/releases/{release_id}/rollback",
    response_model=PipelineRelease,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:pipeline:rollback"))],
)
@limiter.limit("5/minute")
def rollback_release(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    release_id: Annotated[int, Path(ge=1)],
) -> PipelineRelease:
    """Roll back to a prior release by creating a new one with the same snapshot.

    Rollback is strictly append-only — the target release is never mutated or deleted.
    The new release has ``is_rollback=True`` and a ``source_release_id`` pointing
    to the rolled-back release.
    """
    tenant_id = int(user.get("tenant_id", 1))
    published_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    try:
        return service.rollback_release(release_id, tenant_id=tenant_id, published_by=published_by)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Sync — trigger (Phase 1e)
# ------------------------------------------------------------------


@router.post(
    "/connections/{connection_id}/sync",
    response_model=SyncJob,
    status_code=202,
    dependencies=[Depends(require_permission("control_center:sync:run"))],
)
@limiter.limit("10/minute")
def trigger_sync(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    connection_id: Annotated[int, Path(ge=1)],
    body: TriggerSyncRequest,
) -> SyncJob:
    """Trigger a manual sync for the given source connection.

    Creates a ``sync_jobs`` row (and a UUID run id) so the result can be
    tracked via ``GET /connections/{id}/sync-history``.
    """
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    try:
        return service.trigger_sync(
            connection_id,
            tenant_id=tenant_id,
            run_mode=body.run_mode,
            release_id=body.release_id,
            profile_id=body.profile_id,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Sync schedules — Phase 2
# ------------------------------------------------------------------


@router.post(
    "/connections/{connection_id}/schedule",
    response_model=SyncSchedule,
    status_code=201,
    dependencies=[Depends(require_permission("control_center:sync:schedule"))],
)
@limiter.limit("10/minute")
def create_schedule(
    request: Request,
    service: ServiceDep,
    user: UserDep,
    connection_id: Annotated[int, Path(ge=1)],
    body: CreateScheduleRequest,
) -> SyncSchedule:
    """Create a cron schedule that will auto-trigger syncs for the connection.

    ``cron_expr`` must be a 5-field UNIX cron expression (e.g. ``'0 6 * * *'``).
    APScheduler picks up new schedules on next startup; to apply immediately
    you can restart the scheduler or call the internal reload endpoint.
    """
    tenant_id = int(user.get("tenant_id", 1))
    created_by: str = str(user.get("sub") or user.get("user_id") or "anonymous")
    try:
        return service.create_schedule(
            connection_id=connection_id,
            tenant_id=tenant_id,
            cron_expr=body.cron_expr,
            is_active=body.is_active,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/connections/{connection_id}/schedules",
    response_model=SyncScheduleList,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def list_schedules(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SyncScheduleList:
    """List cron schedules for a source connection."""
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    return service.list_schedules(connection_id=connection_id, page=page, page_size=page_size)


@router.delete(
    "/connections/{connection_id}/schedule/{schedule_id}",
    status_code=204,
    dependencies=[Depends(require_permission("control_center:sync:schedule"))],
)
@limiter.limit("10/minute")
def delete_schedule(
    request: Request,
    service: ServiceDep,
    connection_id: Annotated[int, Path(ge=1)],
    schedule_id: Annotated[int, Path(ge=1)],
) -> None:
    """Delete a cron schedule permanently.

    The schedule is removed immediately; the APScheduler job will be
    deregistered on next scheduler reload.
    """
    if service.get_connection(connection_id) is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    found = service.delete_schedule(schedule_id)
    if not found:
        raise HTTPException(status_code=404, detail="schedule_not_found")
