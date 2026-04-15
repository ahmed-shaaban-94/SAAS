"""Analytics ranking endpoints — top products, customers, staff, movers, sites, filters."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.analytics.models import (
    FilterOptions,
    RankingResult,
    StaffQuota,
    TopMovers,
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
    return service.get_product_insights(to_filter(params))


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
    return service.get_customer_insights(to_filter(params))


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
    return service.get_staff_leaderboard(to_filter(params))


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
    return service.get_site_comparison(to_filter(params))


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
    return service.get_top_movers(entity_type, to_filter(params), limit)
