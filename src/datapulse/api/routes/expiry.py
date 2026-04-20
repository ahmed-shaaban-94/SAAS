"""Expiry & Batch Tracking API endpoints.

All endpoints require the ``expiry_tracking`` plan feature flag and
``expiry:read`` (or ``expiry:write``) RBAC permission.
Only available when ``feature_platform`` is enabled in settings.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_tenant_plan_limits
from datapulse.api.limiter import limiter
from datapulse.billing.plans import PlanLimits
from datapulse.expiry.models import (
    BatchInfo,
    ExpiryAlert,
    ExpiryCalendarDay,
    ExpiryExposureTier,
    ExpiryFilter,
    ExpirySummary,
    FefoRequest,
    FefoResponse,
    QuarantineRequest,
    WriteOffRequest,
)
from datapulse.expiry.service import ExpiryService
from datapulse.rbac.dependencies import require_permission

router = APIRouter(
    prefix="/expiry",
    tags=["expiry"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _check_expiry_plan(limits: PlanLimits) -> None:
    if not limits.expiry_tracking:
        raise HTTPException(
            status_code=403,
            detail="Expiry tracking requires Pro plan or above",
        )


from datapulse.api.deps import get_expiry_service  # noqa: E402

ServiceDep = Annotated[ExpiryService, Depends(get_expiry_service)]
PlanDep = Annotated[PlanLimits, Depends(get_tenant_plan_limits)]


def _make_filter(
    site_code: str | None = None,
    drug_code: str | None = None,
    alert_level: str | None = None,
    days_threshold: int = 90,
    limit: int = 100,
) -> ExpiryFilter:
    return ExpiryFilter(
        site_code=site_code,
        drug_code=drug_code,
        alert_level=alert_level,
        days_threshold=days_threshold,
        limit=limit,
    )


# ------------------------------------------------------------------
# 1. GET /expiry/batches — list all active batches
# ------------------------------------------------------------------


@router.get("/batches", response_model=list[BatchInfo])
@limiter.limit("100/minute")
def get_batches(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    site_code: str | None = None,
    drug_code: str | None = None,
    alert_level: str | None = None,
    limit: int = 100,
) -> list[BatchInfo]:
    """Return active batches with computed expiry alert level."""
    _check_expiry_plan(limits)
    set_cache_headers(response, 300)
    return service.get_batches(
        _make_filter(site_code=site_code, drug_code=drug_code, alert_level=alert_level, limit=limit)
    )


# ------------------------------------------------------------------
# 2. GET /expiry/batches/{drug_code} — batches for a single drug
# ------------------------------------------------------------------


@router.get("/batches/{drug_code}", response_model=list[BatchInfo])
@limiter.limit("100/minute")
def get_batches_by_drug(
    request: Request,
    response: Response,
    drug_code: Annotated[str, Path(max_length=100)],
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    site_code: str | None = None,
    limit: int = 100,
) -> list[BatchInfo]:
    """Return all batches for a specific drug across all sites."""
    _check_expiry_plan(limits)
    set_cache_headers(response, 300)
    return service.get_batches_by_drug(drug_code, _make_filter(site_code=site_code, limit=limit))


# ------------------------------------------------------------------
# 3. GET /expiry/alerts — near-expiry alerts
# ------------------------------------------------------------------


@router.get("/alerts", response_model=list[ExpiryAlert])
@limiter.limit("60/minute")
def get_expiry_alerts(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    days_threshold: int = 90,
    site_code: str | None = None,
    drug_code: str | None = None,
    limit: int = 100,
) -> list[ExpiryAlert]:
    """Return batches expiring within the given threshold (30/60/90 days)."""
    _check_expiry_plan(limits)
    set_cache_headers(response, 120)
    return service.get_near_expiry(
        days_threshold,
        _make_filter(site_code=site_code, drug_code=drug_code, limit=limit),
    )


# ------------------------------------------------------------------
# 4. GET /expiry/expired — batches already past expiry date
# ------------------------------------------------------------------


@router.get("/expired", response_model=list[ExpiryAlert])
@limiter.limit("60/minute")
def get_expired_batches(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    site_code: str | None = None,
    limit: int = 100,
) -> list[ExpiryAlert]:
    """Return batches that have already passed their expiry date."""
    _check_expiry_plan(limits)
    set_cache_headers(response, 120)
    return service.get_expired(_make_filter(site_code=site_code, limit=limit))


# ------------------------------------------------------------------
# 5. GET /expiry/summary — aggregated expiry counts per site
# ------------------------------------------------------------------


@router.get("/summary", response_model=list[ExpirySummary])
@limiter.limit("60/minute")
def get_expiry_summary(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    site_code: str | None = None,
) -> list[ExpirySummary]:
    """Return expiry counts (expired/near_expiry/active) aggregated per site."""
    _check_expiry_plan(limits)
    set_cache_headers(response, 300)
    return service.get_expiry_summary(_make_filter(site_code=site_code))


# ------------------------------------------------------------------
# 5b. GET /expiry/exposure-summary — tenant-aggregate EGP per 30/60/90 tier
# ------------------------------------------------------------------


@router.get("/exposure-summary", response_model=list[ExpiryExposureTier])
@limiter.limit("60/minute")
def get_expiry_exposure_summary(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    site_code: str | None = None,
) -> list[ExpiryExposureTier]:
    """Return tenant-wide EGP exposure per 30/60/90 expiry tier.

    Always returns exactly three rows so the frontend can render deterministic
    summary chips even when a tier has zero exposure. Feeds the design-handoff
    Expiry card on `/dashboard/v3` (issue #506).
    """
    _check_expiry_plan(limits)
    set_cache_headers(response, 300)
    return service.get_exposure_tiers(_make_filter(site_code=site_code))


# ------------------------------------------------------------------
# 6. GET /expiry/calendar — day-by-day expiry counts
# ------------------------------------------------------------------


@router.get("/calendar", response_model=list[ExpiryCalendarDay])
@limiter.limit("30/minute")
def get_expiry_calendar(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
    start_date: date | None = None,
    end_date: date | None = None,
    site_code: str | None = None,
) -> list[ExpiryCalendarDay]:
    """Return day-by-day expiry counts for the calendar view."""
    _check_expiry_plan(limits)
    from datetime import timedelta

    today = date.today()
    start = start_date or today
    end = end_date or (today + timedelta(days=90))
    set_cache_headers(response, 300)
    return service.get_expiry_calendar(start, end, _make_filter(site_code=site_code))


# ------------------------------------------------------------------
# 7. POST /expiry/quarantine — quarantine a batch
# ------------------------------------------------------------------


@router.post("/quarantine", status_code=200)
@limiter.limit("30/minute")
def quarantine_batch(
    request: Request,
    body: QuarantineRequest,
    service: ServiceDep,
    limits: PlanDep,
    user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("expiry:write"))],
) -> dict:
    """Move a batch to quarantine status and create a stock adjustment event."""
    _check_expiry_plan(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    service.quarantine_batch(tenant_id, body)
    return {"status": "quarantined", "batch_number": body.batch_number}


# ------------------------------------------------------------------
# 8. POST /expiry/write-off — write off a batch
# ------------------------------------------------------------------


@router.post("/write-off", status_code=200)
@limiter.limit("30/minute")
def write_off_batch(
    request: Request,
    body: WriteOffRequest,
    service: ServiceDep,
    limits: PlanDep,
    user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("expiry:write"))],
) -> dict:
    """Write off a batch quantity and record the reason."""
    _check_expiry_plan(limits)
    tenant_id = int(user.get("tenant_id", "1"))
    service.write_off_batch(tenant_id, body)
    return {
        "status": "written_off",
        "batch_number": body.batch_number,
        "quantity": float(body.quantity),
    }


# ------------------------------------------------------------------
# 9. POST /expiry/fefo — FEFO batch selection
# ------------------------------------------------------------------


@router.post("/fefo", response_model=FefoResponse)
@limiter.limit("60/minute")
def select_fefo(
    request: Request,
    body: FefoRequest,
    service: ServiceDep,
    limits: PlanDep,
    _: Annotated[None, Depends(require_permission("expiry:read"))],
) -> FefoResponse:
    """Select batches using FEFO (First Expiry First Out) for a dispense request."""
    _check_expiry_plan(limits)
    return service.select_fefo(body)
