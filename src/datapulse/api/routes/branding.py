"""Tenant branding & white-label API endpoints.

Provides branding CRUD under ``/branding/`` and a public endpoint
for domain-based branding resolution (no auth required).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.branding.models import (
    BrandingResponse,
    BrandingUpdate,
    PublicBrandingResponse,
)
from datapulse.branding.repository import BrandingRepository
from datapulse.branding.service import BrandingService
from datapulse.core.db import get_session_factory

_logger = structlog.get_logger()

# Authenticated router
router = APIRouter(
    prefix="/branding",
    tags=["branding"],
    dependencies=[Depends(get_current_user)],
)

# Public router (no auth — used by login page)
public_router = APIRouter(
    prefix="/branding",
    tags=["branding"],
)


# ------------------------------------------------------------------
# Dependency injection
# ------------------------------------------------------------------


def get_branding_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> BrandingService:
    repo = BrandingRepository(session)
    return BrandingService(repo)


ServiceDep = Annotated[BrandingService, Depends(get_branding_service)]


# ------------------------------------------------------------------
# Authenticated endpoints
# ------------------------------------------------------------------


@router.get("/", response_model=BrandingResponse)
@limiter.limit("60/minute")
def get_branding(
    request: Request,
    response: Response,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> BrandingResponse:
    """Get the current tenant branding configuration."""
    tenant_id = int(user.get("tenant_id", "1"))
    set_cache_headers(response, 300)
    return service.get_branding(tenant_id)


@router.put("/", response_model=BrandingResponse)
@limiter.limit("5/minute")
def update_branding(
    request: Request,
    data: BrandingUpdate,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> BrandingResponse:
    """Update tenant branding configuration (owner/admin only)."""
    tenant_id = int(user.get("tenant_id", "1"))
    try:
        return service.update_branding(tenant_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/logo", response_model=BrandingResponse)
@limiter.limit("5/minute")
def delete_logo(
    request: Request,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> BrandingResponse:
    """Remove the tenant logo."""
    tenant_id = int(user.get("tenant_id", "1"))
    return service.delete_logo(tenant_id)


# ------------------------------------------------------------------
# Public endpoint (no auth)
# ------------------------------------------------------------------


def _get_raw_session() -> Generator[Session, None, None]:
    """Unauthenticated DB session for public lookups (no RLS)."""
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL statement_timeout = '10s'"))
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@public_router.get("/public", response_model=PublicBrandingResponse)
@limiter.limit("60/minute")
def get_public_branding(
    request: Request,
    response: Response,
    domain: str = Query(..., description="Custom domain or subdomain to look up"),
    *,
    session: Annotated[Session, Depends(_get_raw_session)],
) -> PublicBrandingResponse:
    """Get public branding by domain (no auth required, for login page)."""
    repo = BrandingRepository(session)
    service = BrandingService(repo)
    response.headers["Cache-Control"] = "max-age=600, public"
    return service.get_public_branding(domain)
