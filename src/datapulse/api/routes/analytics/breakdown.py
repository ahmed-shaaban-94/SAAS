"""Analytics breakdown endpoints — billing, customer-type, origin, products, seasonality."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.analytics.models import (
    BillingBreakdown,
    CustomerTypeBreakdown,
    HeatmapData,
    LifecycleDistribution,
    ProductHierarchy,
    ProductLifecycle,
    RevenueDailyRolling,
    RevenueSiteRolling,
    SeasonalityDaily,
    SeasonalityMonthly,
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
    return service.get_billing_breakdown(to_filter(params))


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
    return service.get_customer_type_breakdown(to_filter(params))


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
    return service.get_origin_breakdown(to_filter(params))


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
    return service.get_product_hierarchy(to_filter(params))


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
