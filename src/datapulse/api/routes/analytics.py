"""Analytics API endpoints.

Provides 10 GET endpoints under ``/analytics/`` for dashboard consumption.
All endpoints accept common query parameters (date range, category, brand,
site, staff, limit) converted to an ``AnalyticsFilter`` via a shared helper.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, Field

from datapulse.analytics.models import (
    ABCAnalysis,
    AnalyticsFilter,
    BillingBreakdown,
    CustomerAnalytics,
    CustomerTypeBreakdown,
    DashboardData,
    DataDateRange,
    DateRange,
    FilterOptions,
    HeatmapData,
    KPISummary,
    ProductHierarchy,
    ProductPerformance,
    RankingResult,
    ReturnAnalysis,
    ReturnsTrend,
    SegmentSummary,
    SiteDetail,
    StaffPerformance,
    TopMovers,
    TrendResult,
)
from datapulse.analytics.service import AnalyticsService
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_analytics_service
from datapulse.api.limiter import limiter

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Cache-Control helper
# ------------------------------------------------------------------


def _set_cache(response: Response, max_age: int) -> None:
    """Set Cache-Control header for browser caching (always private for RLS)."""
    response.headers["Cache-Control"] = f"max-age={max_age}, private"


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
            detail="Both start_date and end_date are required when filtering by date range.",
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


@router.get("/dashboard", response_model=DashboardData)
@limiter.limit("60/minute")
def get_dashboard(
    request: Request,
    response: Response,
    service: ServiceDep,
    target_date: Annotated[date | None, Query()] = None,
) -> DashboardData:
    """Composite dashboard endpoint — KPI + trends + rankings + filters in one call."""
    _set_cache(response, 600)
    return service.get_dashboard_data(target_date)


@router.get("/date-range", response_model=DataDateRange)
@limiter.limit("100/minute")
def get_date_range(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> DataDateRange:
    """Return the min/max dates of available data for frontend preset calculation."""
    _set_cache(response, 3600)
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
    _set_cache(response, 600)
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
    _set_cache(response, 300)
    filters = _to_filter(params)
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
    _set_cache(response, 300)
    filters = _to_filter(params)
    return service.get_monthly_trend(filters)


@router.get("/products/top", response_model=RankingResult)
@limiter.limit("100/minute")
def get_top_products(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Top products ranked by net revenue."""
    _set_cache(response, 300)
    return service.get_product_insights(_to_filter(params))


@router.get("/customers/top", response_model=RankingResult)
@limiter.limit("100/minute")
def get_top_customers(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Top customers ranked by net revenue."""
    _set_cache(response, 300)
    return service.get_customer_insights(_to_filter(params))


@router.get("/staff/top", response_model=RankingResult)
@limiter.limit("100/minute")
def get_top_staff(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Staff leaderboard ranked by net revenue."""
    _set_cache(response, 300)
    return service.get_staff_leaderboard(_to_filter(params))


@router.get("/sites", response_model=RankingResult)
@limiter.limit("100/minute")
def get_sites(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> RankingResult:
    """Site comparison ranked by net revenue."""
    _set_cache(response, 300)
    return service.get_site_comparison(_to_filter(params))


@router.get("/filters/options", response_model=FilterOptions)
@limiter.limit("100/minute")
def get_filter_options(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> FilterOptions:
    """Return available filter values for slicer/dropdown population."""
    _set_cache(response, 3600)
    return service.get_filter_options()


@router.get("/billing-breakdown", response_model=BillingBreakdown)
@limiter.limit("60/minute")
def get_billing_breakdown(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> BillingBreakdown:
    """Billing method distribution (cash, credit, delivery, etc.)."""
    _set_cache(response, 300)
    return service.get_billing_breakdown(_to_filter(params))


@router.get("/customer-type-breakdown", response_model=CustomerTypeBreakdown)
@limiter.limit("60/minute")
def get_customer_type_breakdown(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> CustomerTypeBreakdown:
    """Walk-in vs insurance vs other distribution by month."""
    _set_cache(response, 300)
    return service.get_customer_type_breakdown(_to_filter(params))


@router.get("/top-movers", response_model=TopMovers)
@limiter.limit("60/minute")
def get_top_movers(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
    entity_type: Annotated[str, Query(pattern="^(product|customer|staff)$")] = "product",
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> TopMovers:
    """Top gainers and losers vs previous period."""
    _set_cache(response, 300)
    return service.get_top_movers(entity_type, _to_filter(params), limit)


@router.get("/products/by-category", response_model=ProductHierarchy)
@limiter.limit("60/minute")
def get_product_hierarchy(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> ProductHierarchy:
    """Product hierarchy: Category > Brand > Product."""
    _set_cache(response, 300)
    return service.get_product_hierarchy(_to_filter(params))


@router.get("/returns", response_model=list[ReturnAnalysis])
@limiter.limit("100/minute")
def get_returns(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> list[ReturnAnalysis]:
    """Top returns/credit notes by amount."""
    _set_cache(response, 300)
    return service.get_return_report(_to_filter(params))


@router.get("/sites/{site_key}", response_model=SiteDetail)
@limiter.limit("100/minute")
def get_site_detail(
    request: Request,
    response: Response,
    site_key: Annotated[int, Path(ge=1, description="Site surrogate key")],
    service: ServiceDep,
) -> SiteDetail:
    """Detailed site metrics with monthly trend."""
    _set_cache(response, 300)
    result = service.get_site_detail(site_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return result


@router.get("/products/{product_key}", response_model=ProductPerformance)
@limiter.limit("100/minute")
def get_product_detail(
    request: Request,
    response: Response,
    product_key: Annotated[int, Path(ge=1, description="Product surrogate key")],
    service: ServiceDep,
) -> ProductPerformance:
    """Detailed product performance metrics."""
    _set_cache(response, 300)
    result = service.get_product_detail(product_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.get("/customers/{customer_key}", response_model=CustomerAnalytics)
@limiter.limit("100/minute")
def get_customer_detail(
    request: Request,
    response: Response,
    customer_key: Annotated[int, Path(ge=1, description="Customer surrogate key")],
    service: ServiceDep,
) -> CustomerAnalytics:
    """Detailed customer analytics."""
    _set_cache(response, 300)
    result = service.get_customer_detail(customer_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


@router.get("/staff/{staff_key}", response_model=StaffPerformance)
@limiter.limit("100/minute")
def get_staff_detail(
    request: Request,
    response: Response,
    staff_key: Annotated[int, Path(ge=1, description="Staff surrogate key")],
    service: ServiceDep,
) -> StaffPerformance:
    """Detailed staff performance metrics."""
    _set_cache(response, 300)
    result = service.get_staff_detail(staff_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return result


# ------------------------------------------------------------------
# Phase 5: CEO Review — Advanced Analytics
# ------------------------------------------------------------------


@router.get("/abc-analysis", response_model=ABCAnalysis)
@limiter.limit("60/minute")
def get_abc_analysis(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
    entity: Annotated[str, Query(pattern="^(product|customer)$")] = "product",
) -> ABCAnalysis:
    """ABC/Pareto analysis for products or customers."""
    _set_cache(response, 300)
    return service.get_abc_analysis(entity, _to_filter(params))


@router.get("/heatmap", response_model=HeatmapData)
@limiter.limit("60/minute")
def get_heatmap(
    request: Request,
    response: Response,
    service: ServiceDep,
    year: Annotated[int, Query(ge=2020, le=2030)] = 2025,
) -> HeatmapData:
    """Calendar heatmap — daily revenue for a year."""
    _set_cache(response, 300)
    return service.get_heatmap(year)


@router.get("/returns/trend", response_model=ReturnsTrend)
@limiter.limit("60/minute")
def get_returns_trend(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> ReturnsTrend:
    """Monthly returns trend."""
    _set_cache(response, 300)
    return service.get_returns_trend(_to_filter(params))


@router.get("/segments/summary", response_model=list[SegmentSummary])
@limiter.limit("60/minute")
def get_segment_summary(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[SegmentSummary]:
    """Customer RFM segment summary."""
    _set_cache(response, 300)
    return service.get_segment_summary()
