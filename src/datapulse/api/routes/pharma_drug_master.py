"""Pharma drug-master catalog and EDA reporting API endpoints.

Routes:
    GET  /pharma/drug-master            — search catalog
    GET  /pharma/drug-master/{ean13}    — get by EAN-13
    POST /pharma/drug-master/import     — bulk import (admin only)
    POST /pharma/eda-export             — generate EDA export (admin only)
    GET  /pharma/eda-exports            — list past exports (admin only)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_drug_master_service
from datapulse.api.limiter import limiter
from datapulse.core.auth import UserClaims
from datapulse.pharma.models import (
    DrugMasterEntry,
    DrugMasterImportResult,
    DrugMasterSearchResult,
    EDAExport,
    EDAExportRequest,
)
from datapulse.pharma.service import DrugMasterService
from datapulse.rbac.dependencies import require_role

router = APIRouter(
    prefix="/pharma",
    tags=["pharma"],
    dependencies=[Depends(get_current_user)],
)

ServiceDep = Annotated[DrugMasterService, Depends(get_drug_master_service)]
CurrentUserDep = Annotated[UserClaims, Depends(get_current_user)]


# ── 1. GET /pharma/drug-master ─────────────────────────────────────────────


@router.get("/drug-master", response_model=list[DrugMasterSearchResult])
@limiter.limit("120/minute")
def search_drug_master(
    request: Request,
    response: Response,
    service: ServiceDep,
    q: str = Query(default="", max_length=200, description="Search query (name EN/AR or EAN-13)"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[DrugMasterSearchResult]:
    """Search the shared drug master catalog."""
    set_cache_headers(response, 60)
    return service.search_catalog(q, limit)


# ── 2. GET /pharma/drug-master/{ean13} ────────────────────────────────────


@router.get("/drug-master/{ean13}", response_model=DrugMasterSearchResult)
@limiter.limit("120/minute")
def get_drug_by_ean13(
    request: Request,
    response: Response,
    ean13: str,
    service: ServiceDep,
) -> DrugMasterSearchResult:
    """Return a single drug catalog entry by EAN-13 code."""
    entry = service.get_by_ean13(ean13)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Drug with EAN-13 '{ean13}' not found")
    set_cache_headers(response, 300)
    return entry


# ── 3. POST /pharma/drug-master/import ────────────────────────────────────


@router.post(
    "/drug-master/import",
    response_model=DrugMasterImportResult,
    dependencies=[Depends(require_role("owner", "admin"))],
)
@limiter.limit("5/minute")
def import_drug_master(
    request: Request,
    entries: list[DrugMasterEntry],
    service: ServiceDep,
) -> DrugMasterImportResult:
    """Bulk-import or update drug catalog entries (admin/owner only).

    Rows missing an EAN-13 are skipped and counted in ``rows_skipped``.
    """
    if not entries:
        raise HTTPException(status_code=400, detail="Entry list must not be empty")
    return service.import_catalog(entries)


# ── 4. POST /pharma/eda-export ─────────────────────────────────────────────


@router.post(
    "/eda-export",
    response_model=EDAExport,
    dependencies=[Depends(require_role("owner", "admin"))],
)
@limiter.limit("5/minute")
def generate_eda_export(
    request: Request,
    body: EDAExportRequest,
    service: ServiceDep,
    user: CurrentUserDep,
) -> EDAExport:
    """Generate a new EDA (Egyptian Drug Authority) export CSV (admin/owner only).

    Queries controlled-substance or all-monthly transactions, writes a
    CSV file to the configured export directory, and records the metadata.
    """
    tenant_id = int(user.get("tenant_id", "1"))
    created_by = user.get("email", user.get("sub", "unknown"))

    if body.period_end < body.period_start:
        raise HTTPException(
            status_code=422,
            detail="period_end must be on or after period_start",
        )

    return service.generate_eda_export(tenant_id, body, created_by)


# ── 5. GET /pharma/eda-exports ─────────────────────────────────────────────


@router.get(
    "/eda-exports",
    response_model=list[EDAExport],
    dependencies=[Depends(require_role("owner", "admin"))],
)
@limiter.limit("60/minute")
def list_eda_exports(
    request: Request,
    response: Response,
    service: ServiceDep,
    user: CurrentUserDep,
) -> list[EDAExport]:
    """List all past EDA export records for the current tenant (admin/owner only)."""
    tenant_id = int(user.get("tenant_id", "1"))
    set_cache_headers(response, 60)
    return service.list_eda_exports(tenant_id)
