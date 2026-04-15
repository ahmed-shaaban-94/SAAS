"""Analytics detail endpoints — sites, products, customers, staff, affinity, waterfall."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from datapulse.analytics.models import (
    AffinityPair,
    CustomerAnalytics,
    ProductPerformance,
    SiteDetail,
    StaffPerformance,
    WaterfallAnalysis,
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


@router.get("/products/{product_key}/affinity", response_model=list[AffinityPair])
@limiter.limit("60/minute")
def get_product_affinity(
    request: Request,
    response: Response,
    service: ServiceDep,
    product_key: int,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list:
    """Top co-purchased products for a given product."""
    set_cache_headers(response, 600)
    rows = service.get_affinity_for_product(product_key, limit=limit)
    return [AffinityPair(**r) for r in rows]


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
    return service.get_why_changed(to_filter(params), limit=driver_limit)
