"""Analytics KPI endpoints — dashboard, summary, trends, segments."""

from __future__ import annotations

from datetime import date
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
from datapulse.api.limiter import limiter
from datapulse.api.routes.analytics._shared import (
    AnalyticsQueryParams,
    ServiceDep,
    to_filter,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


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
    target_date: Annotated[date | None, Query()] = None,
) -> KPISummary:
    """Executive KPI snapshot for the dashboard header."""
    set_cache_headers(response, 600)
    return service.get_dashboard_summary(target_date)


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
