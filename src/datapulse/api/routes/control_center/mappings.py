"""Control Center — mapping template endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.api.routes.control_center._deps import ServiceDep
from datapulse.control_center.models import (
    CreateMappingRequest,
    MappingTemplate,
    MappingTemplateList,
    UpdateMappingRequest,
    ValidateMappingRequest,
    ValidationReport,
)
from datapulse.rbac.dependencies import require_permission

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter()


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
