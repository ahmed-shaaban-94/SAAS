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
from sqlalchemy.orm import Session

from datapulse.analytics.affinity_repository import AffinityRepository
from datapulse.analytics.churn_repository import ChurnRepository
from datapulse.analytics.models import (
    ABCAnalysis,
    AffinityPair,
    AnalyticsFilter,
    BillingBreakdown,
    ChurnPrediction,
    CustomerAnalytics,
    CustomerHealthScore,
    CustomerTypeBreakdown,
    DashboardData,
    DataDateRange,
    DateRange,
    FilterOptions,
    HealthDistribution,
    HeatmapData,
    KPISummary,
    LifecycleDistribution,
    ProductHierarchy,
    ProductLifecycle,
    ProductPerformance,
    RankingResult,
    ReturnAnalysis,
    ReturnsTrend,
    RevenueDailyRolling,
    RevenueSiteRolling,
    SeasonalityDaily,
    SeasonalityMonthly,
    SegmentSummary,
    SiteDetail,
    StaffPerformance,
    StaffQuota,
    TopMovers,
    TrendResult,
    WaterfallAnalysis,
)
from datapulse.analytics.service import AnalyticsService
from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_analytics_service, get_tenant_session
from datapulse.api.limiter import limiter

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
)


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
    params: Annotated[AnalyticsQueryParams, Depends()],
    target_date: Annotated[date | None, Query()] = None,
) -> DashboardData:
    """Composite dashboard endpoint — KPI + trends + rankings + filters in one call.

    Accepts all standard analytics filters (date range, site, category, brand, staff).
    Falls back to a 30-day window from the latest data date when no range is given.
    """
    set_cache_headers(response, 600)
    filters = _to_filter(params)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
    return service.get_site_comparison(_to_filter(params))


@router.get("/filters/options", response_model=FilterOptions)
@limiter.limit("100/minute")
def get_filter_options(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> FilterOptions:
    """Return available filter values for slicer/dropdown population."""
    set_cache_headers(response, 3600)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
    return service.get_customer_type_breakdown(_to_filter(params))


@router.get("/origin-breakdown")
@limiter.limit("60/minute")
def get_origin_breakdown(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
) -> list[dict]:
    """Revenue breakdown by product origin (Pharma, Non-pharma, HVI, etc.)."""
    set_cache_headers(response, 300)
    return service.get_origin_breakdown(_to_filter(params))


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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
    result = service.get_product_detail(product_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.get("/customers/churn", response_model=list[ChurnPrediction])
@limiter.limit("60/minute")
def get_churn_predictions(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_tenant_session)],
    risk_level: str | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list:
    """Customer churn predictions sorted by probability."""
    set_cache_headers(response, 300)
    repo = ChurnRepository(session)
    rows = repo.get_churn_predictions(risk_level=risk_level, limit=limit)
    return [ChurnPrediction(**r) for r in rows]


@router.get("/customers/{customer_key}", response_model=CustomerAnalytics)
@limiter.limit("100/minute")
def get_customer_detail(
    request: Request,
    response: Response,
    customer_key: Annotated[int, Path(ge=1, description="Customer surrogate key")],
    service: ServiceDep,
) -> CustomerAnalytics:
    """Detailed customer analytics."""
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
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
    set_cache_headers(response, 300)
    return service.get_returns_trend(_to_filter(params))


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


# ------------------------------------------------------------------
# Enhancement 4: Analytics Intelligence
# ------------------------------------------------------------------


@router.get("/why-changed", response_model=WaterfallAnalysis)
@limiter.limit("60/minute")
def get_why_changed(
    request: Request,
    response: Response,
    service: ServiceDep,
    params: Annotated[AnalyticsQueryParams, Depends()],
    driver_limit: Annotated[int, Query(ge=1, le=50)] = 15,
) -> WaterfallAnalysis:
    """Revenue change decomposition — why did revenue change?"""
    set_cache_headers(response, 300)
    return service.get_why_changed(_to_filter(params), limit=driver_limit)


@router.get("/customer-health", response_model=list[CustomerHealthScore])
@limiter.limit("60/minute")
def get_customer_health(
    request: Request,
    response: Response,
    service: ServiceDep,
    band: Annotated[str | None, Query(max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[CustomerHealthScore]:
    """Customer health scores with optional band filter."""
    set_cache_headers(response, 300)
    return service.get_customer_health(band=band, limit=limit)


@router.get("/customer-health/distribution", response_model=HealthDistribution)
@limiter.limit("60/minute")
def get_health_distribution(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> HealthDistribution:
    """Distribution of customers across health bands."""
    set_cache_headers(response, 300)
    return service.get_health_distribution()


@router.get("/customer-health/at-risk", response_model=list[CustomerHealthScore])
@limiter.limit("60/minute")
def get_at_risk_customers(
    request: Request,
    response: Response,
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CustomerHealthScore]:
    """At-risk and critical customers, lowest score first."""
    set_cache_headers(response, 300)
    return service.get_at_risk_customers(limit=limit)


@router.get("/staff/quota", response_model=list[StaffQuota])
@limiter.limit("60/minute")
def get_staff_quota(
    request: Request,
    response: Response,
    service: ServiceDep,
    year: int | None = Query(None),
    month: int | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list:
    """Staff quota attainment — actual vs target per staff member."""
    set_cache_headers(response, 300)
    rows = service._repo.get_staff_quota(year=year, month=month, limit=limit)
    return [StaffQuota(**r) for r in rows]


@router.get("/products/{product_key}/affinity", response_model=list[AffinityPair])
@limiter.limit("60/minute")
def get_product_affinity(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_tenant_session)],
    product_key: int,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list:
    """Top co-purchased products for a given product."""
    set_cache_headers(response, 600)
    repo = AffinityRepository(session)
    rows = repo.get_affinity_for_product(product_key, limit=limit)
    return [AffinityPair(**r) for r in rows]


# ------------------------------------------------------------------
# Feature Store: Revenue Rolling, Seasonality, Product Lifecycle
# ------------------------------------------------------------------


@router.get("/revenue/rolling", response_model=list[RevenueDailyRolling])
@limiter.limit("60/minute")
def get_revenue_daily_rolling(
    request: Request,
    response: Response,
    service: ServiceDep,
    days: Annotated[int, Query(ge=1, le=730)] = 90,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[RevenueDailyRolling]:
    """Daily revenue with 7/30/90-day MAs, volatility, and trend ratios."""
    set_cache_headers(response, 300)
    return service.get_revenue_daily_rolling(days=days, limit=limit)


@router.get("/revenue/rolling/by-site", response_model=list[RevenueSiteRolling])
@limiter.limit("60/minute")
def get_revenue_site_rolling(
    request: Request,
    response: Response,
    service: ServiceDep,
    site_key: int | None = Query(None),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[RevenueSiteRolling]:
    """Per-site daily rolling MAs with cross-site comparison."""
    set_cache_headers(response, 300)
    return service.get_revenue_site_rolling(site_key=site_key, days=days, limit=limit)


@router.get("/seasonality/monthly", response_model=list[SeasonalityMonthly])
@limiter.limit("60/minute")
def get_seasonality_monthly(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[SeasonalityMonthly]:
    """Monthly seasonal indices (12 rows) for forecasting and pattern analysis."""
    set_cache_headers(response, 600)
    return service.get_seasonality_monthly()


@router.get("/seasonality/daily", response_model=list[SeasonalityDaily])
@limiter.limit("60/minute")
def get_seasonality_daily(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[SeasonalityDaily]:
    """Day-of-week seasonal indices (7 rows) for scheduling and pattern analysis."""
    set_cache_headers(response, 600)
    return service.get_seasonality_daily()


@router.get("/products/lifecycle", response_model=list[ProductLifecycle])
@limiter.limit("60/minute")
def get_product_lifecycle(
    request: Request,
    response: Response,
    service: ServiceDep,
    phase: Annotated[str | None, Query(pattern="^(Growth|Mature|Decline|Dormant)$")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ProductLifecycle]:
    """Product lifecycle classification with optional phase filter."""
    set_cache_headers(response, 300)
    return service.get_product_lifecycle(phase=phase, limit=limit)


@router.get("/products/lifecycle/distribution", response_model=LifecycleDistribution)
@limiter.limit("60/minute")
def get_lifecycle_distribution(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> LifecycleDistribution:
    """Distribution of products across lifecycle phases."""
    set_cache_headers(response, 300)
    return service.get_lifecycle_distribution()
