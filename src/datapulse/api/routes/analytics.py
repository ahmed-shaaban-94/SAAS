"""Analytics API endpoints.

Provides 10 GET endpoints under ``/analytics/`` for dashboard consumption.
All endpoints accept common query parameters (date range, category, brand,
site, staff, limit) converted to an ``AnalyticsFilter`` via a shared helper.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from datapulse.api.limiter import limiter

from datapulse.analytics.models import (
    AnalyticsFilter,
    CustomerAnalytics,
    DateRange,
    KPISummary,
    ProductPerformance,
    RankingResult,
    ReturnAnalysis,
    TrendResult,
)
from datapulse.analytics.service import AnalyticsService
from datapulse.api.deps import get_analytics_service, verify_api_key

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(verify_api_key)])


# ------------------------------------------------------------------
# Query parameter model
# ------------------------------------------------------------------


class AnalyticsQueryParams(BaseModel):
    """Common query parameters shared across analytics endpoints."""

    start_date: date | None = None
    end_date: date | None = None
    category: Annotated[str | None, Field(max_length=100)] = None
    brand: Annotated[str | None, Field(max_length=100)] = None
    site_key: int | None = None
    staff_key: int | None = None
    limit: int = Field(default=10, ge=1, le=100)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _to_filter(params: AnalyticsQueryParams) -> AnalyticsFilter | None:
    """Convert query params into an ``AnalyticsFilter``.

    Returns ``None`` when no params are set so the service layer
    can apply its own 30-day default.
    """
    has_any = (
        params.start_date is not None
        or params.end_date is not None
        or params.category is not None
        or params.brand is not None
        or params.site_key is not None
        or params.staff_key is not None
        or params.limit != 10
    )
    if not has_any:
        return None

    date_range: DateRange | None = None
    if params.start_date is not None and params.end_date is not None:
        date_range = DateRange(
            start_date=params.start_date,
            end_date=params.end_date,
        )
    elif params.start_date is not None or params.end_date is not None:
        raise HTTPException(
            status_code=422,
            detail="Both start_date and end_date are required "
            "when filtering by date range.",
        )

    return AnalyticsFilter(
        date_range=date_range,
        site_key=params.site_key,
        category=params.category,
        brand=params.brand,
        staff_key=params.staff_key,
        limit=params.limit,
    )


# Type alias for dependency injection
ServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("/summary", response_model=KPISummary)
@limiter.limit("100/minute")
def get_summary(
    request: Request,
    service: ServiceDep,
    target_date: Annotated[date | None, Query()] = None,
) -> KPISummary:
    """Executive KPI snapshot for the dashboard header."""
    return service.get_dashboard_summary(target_date)


@router.get("/trends/daily", response_model=TrendResult)
@limiter.limit("100/minute")
def get_daily_trend(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> TrendResult:
    """Daily net-sales trend line."""
    filters = _to_filter(params)
    return service.get_revenue_trends(filters)["daily"]


@router.get("/trends/monthly", response_model=TrendResult)
@limiter.limit("100/minute")
def get_monthly_trend(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> TrendResult:
    """Monthly net-sales trend line."""
    filters = _to_filter(params)
    return service.get_revenue_trends(filters)["monthly"]


@router.get("/products/top", response_model=RankingResult)
@limiter.limit("100/minute")
def get_top_products(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Top products ranked by net revenue."""
    return service.get_product_insights(_to_filter(params))


@router.get("/customers/top", response_model=RankingResult)
@limiter.limit("100/minute")
def get_top_customers(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Top customers ranked by net revenue."""
    return service.get_customer_insights(_to_filter(params))


@router.get("/staff/top", response_model=RankingResult)
@limiter.limit("100/minute")
def get_top_staff(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Staff leaderboard ranked by net revenue."""
    return service.get_staff_leaderboard(_to_filter(params))


@router.get("/sites", response_model=RankingResult)
@limiter.limit("100/minute")
def get_sites(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Site comparison ranked by net revenue."""
    return service.get_site_comparison(_to_filter(params))


@router.get("/returns", response_model=list[ReturnAnalysis])
@limiter.limit("100/minute")
def get_returns(
    request: Request,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> list[ReturnAnalysis]:
    """Top returns/credit notes by amount."""
    return service.get_return_report(_to_filter(params))


@router.get("/products/{product_key}", response_model=ProductPerformance)
@limiter.limit("100/minute")
def get_product_detail(
    request: Request,
    product_key: Annotated[int, Path(ge=1, description="Product surrogate key")],
    service: ServiceDep,
) -> ProductPerformance:
    """Detailed product performance metrics."""
    result = service.get_product_detail(product_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.get("/customers/{customer_key}", response_model=CustomerAnalytics)
@limiter.limit("100/minute")
def get_customer_detail(
    request: Request,
    customer_key: Annotated[int, Path(ge=1, description="Customer surrogate key")],
    service: ServiceDep,
) -> CustomerAnalytics:
    """Detailed customer analytics."""
    result = service.get_customer_detail(customer_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result
