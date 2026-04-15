"""Analytics churn endpoints — churn predictions, returns, ABC analysis."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.analytics.models import (
    ABCAnalysis,
    ChurnPrediction,
    ReturnAnalysis,
    ReturnsTrend,
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


@router.get("/customers/churn", response_model=list[ChurnPrediction])
@limiter.limit("60/minute")
def get_churn_predictions(
    request: Request,
    response: Response,
    service: ServiceDep,
    risk_level: str | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list:
    """Customer churn predictions sorted by probability."""
    set_cache_headers(response, 300)
    rows = service.get_churn_predictions(risk_level=risk_level, limit=limit)
    return [ChurnPrediction(**r) for r in rows]


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
    return service.get_return_report(to_filter(params))


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
    return service.get_returns_trend(to_filter(params))


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
    return service.get_abc_analysis(entity, to_filter(params))
