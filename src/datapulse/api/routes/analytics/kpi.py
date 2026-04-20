"""Analytics KPI endpoints — dashboard, summary, trends, segments."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.analytics.models import (
    DashboardData,
    DataDateRange,
    KPISummary,
    SegmentSummary,
    TrendResult,
)
from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import (
    get_expiry_service,
    get_inventory_service,
    get_tenant_plan_limits,
)
from datapulse.api.limiter import limiter
from datapulse.api.routes.analytics._shared import (
    AnalyticsQueryParams,
    ServiceDep,
    to_filter,
)
from datapulse.billing.plans import PlanLimits
from datapulse.expiry.models import ExpiryFilter
from datapulse.expiry.service import ExpiryService
from datapulse.inventory.models import InventoryFilter
from datapulse.inventory.service import InventoryService
from datapulse.logging import get_logger

log = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _enrich_kpi_row(
    summary: KPISummary,
    limits: PlanLimits,
    inventory_service: InventoryService,
    expiry_service: ExpiryService,
) -> KPISummary:
    """Populate ``stock_risk_count`` / ``expiry_exposure_egp`` when plan allows.

    Failures are logged and swallowed — the dashboard still renders the
    core KPI row if the auxiliary modules are unreachable (degraded view).
    """
    updates: dict[str, object] = {}

    if limits.inventory_management:
        try:
            alerts = inventory_service.get_reorder_alerts(InventoryFilter(limit=500))
            updates["stock_risk_count"] = len(alerts)
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("kpi_stock_risk_failed", error=str(exc))

    if limits.expiry_tracking:
        try:
            rows = expiry_service.get_expiry_summary(ExpiryFilter(limit=500))
            near = [r for r in rows if r.expiry_bucket == "near_expiry"]
            exposure = sum((r.total_value for r in near), Decimal("0"))
            batch_count = sum(r.batch_count for r in near)
            updates["expiry_exposure_egp"] = exposure
            updates["expiry_batch_count"] = batch_count
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("kpi_expiry_exposure_failed", error=str(exc))

    if not updates:
        return summary
    return summary.model_copy(update=updates)


@router.get("/dashboard", response_model=DashboardData)
@limiter.limit("60/minute")
def get_dashboard(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
    target_date: Annotated[date | None, Query()] = None,
) -> DashboardData:
    """Composite dashboard endpoint — KPI + trends + rankings + filters in one call.

    Accepts all standard analytics filters (date range, site, category, brand, staff).
    Falls back to a 30-day window from the latest data date when no range is given.
    """
    set_cache_headers(response, 600)
    filters = to_filter(params)
    return service.get_dashboard_data(target_date=target_date, filters=filters)


@router.get("/date-range", response_model=DataDateRange)
@limiter.limit("100/minute")
def get_date_range(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> DataDateRange:
    """Return the min/max dates of available data for frontend preset calculation."""
    set_cache_headers(response, 3600)
    return service.get_date_range()


@router.get("/summary", response_model=KPISummary)
@limiter.limit("100/minute")
def get_summary(
    request: Request,
    response: Response,
    service: ServiceDep,
    limits: Annotated[PlanLimits, Depends(get_tenant_plan_limits)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
    expiry_service: Annotated[ExpiryService, Depends(get_expiry_service)],
    target_date: Annotated[date | None, Query()] = None,
) -> KPISummary:
    """Executive KPI snapshot for the dashboard header.

    Enriches the core analytics KPI with ``stock_risk_count`` and
    ``expiry_exposure_egp`` when the tenant plan includes the
    ``inventory_management`` / ``expiry_tracking`` features (#503).
    """
    set_cache_headers(response, 600)
    summary = service.get_dashboard_summary(target_date)
    return _enrich_kpi_row(summary, limits, inventory_service, expiry_service)


@router.get("/trends/daily", response_model=TrendResult)
@limiter.limit("100/minute")
def get_daily_trend(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> TrendResult:
    """Daily net-sales trend line."""
    set_cache_headers(response, 300)
    filters = to_filter(params)
    return service.get_daily_trend(filters)


@router.get("/trends/monthly", response_model=TrendResult)
@limiter.limit("100/minute")
def get_monthly_trend(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> TrendResult:
    """Monthly net-sales trend line."""
    set_cache_headers(response, 300)
    filters = to_filter(params)
    return service.get_monthly_trend(filters)


@router.get("/segments/summary", response_model=list[SegmentSummary])
@limiter.limit("60/minute")
def get_segment_summary(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[SegmentSummary]:
    """Customer RFM segment summary."""
    set_cache_headers(response, 300)
    return service.get_segment_summary()
