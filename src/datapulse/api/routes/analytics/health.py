"""Analytics health endpoints — customer health scores and distribution."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.analytics.models import (
    CustomerHealthScore,
    HealthDistribution,
)
from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.limiter import limiter
from datapulse.api.routes.analytics._shared import ServiceDep

router = APIRouter(dependencies=[Depends(get_current_user)])


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
