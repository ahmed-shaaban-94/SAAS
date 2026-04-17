"""Control Center — pipeline profiles, drafts, and releases endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.api.routes.control_center._deps import ServiceDep
from datapulse.control_center.models import (
    CreateDraftRequest,
    CreateProfileRequest,
    PipelineDraft,
    PipelineDraftList,
    PipelineProfile,
    PipelineProfileList,
    PipelineRelease,
    PipelineReleaseList,
    PublishDraftRequest,
    UpdateProfileRequest,
)
from datapulse.rbac.dependencies import require_permission

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter()


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
# Releases — view (admin only)
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
