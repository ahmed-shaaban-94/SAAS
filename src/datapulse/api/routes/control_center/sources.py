"""Control Center — canonical domains, source connections, and health summary endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.api.routes.control_center._deps import ServiceDep
from datapulse.control_center.models import (
    CanonicalDomainList,
    ConnectionPreviewResult,
    ConnectionTestResult,
    CreateConnectionRequest,
    HealthSummary,
    SourceConnection,
    SourceConnectionList,
    UpdateConnectionRequest,
)
from datapulse.rbac.dependencies import require_permission

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]

router = APIRouter()


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
# Health summary — Phase 4
# ------------------------------------------------------------------


@router.get(
    "/health-summary",
    response_model=HealthSummary,
    dependencies=[Depends(require_permission("control_center:connections:view"))],
)
@limiter.limit("60/minute")
def get_health_summary(
    request: Request,
    service: ServiceDep,
    user: UserDep,
) -> HealthSummary:
    """Return aggregated health data for the Control Center dashboard.

    Queries existing tables only — no new tables required.
    """
    tenant_id = int(user.get("tenant_id", 1))
    return service.get_health_summary(tenant_id=tenant_id)
