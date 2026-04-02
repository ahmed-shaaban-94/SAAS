"""Forecasting API endpoints.

Provides endpoints for revenue forecasts, product demand forecasts,
forecast summary, and customer RFM segments from the feature store.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_forecasting_service
from datapulse.api.limiter import limiter
from datapulse.forecasting.models import (
    CustomerSegment,
    ForecastResult,
    ForecastSummary,
)
from datapulse.forecasting.service import ForecastingService

router = APIRouter(
    prefix="/forecasting",
    tags=["forecasting"],
    dependencies=[Depends(get_current_user)],
)


def _set_cache(response: Response, max_age: int) -> None:
    """Set Cache-Control header (always private for RLS)."""
    response.headers["Cache-Control"] = f"max-age={max_age}, private"


ForecastServiceDep = Annotated[ForecastingService, Depends(get_forecasting_service)]


@router.get("/revenue", response_model=ForecastResult)
@limiter.limit("60/minute")
def get_revenue_forecast(
    request: Request,
    response: Response,
    service: ForecastServiceDep,
    granularity: Annotated[str, Query(pattern="^(daily|monthly)$")] = "daily",
) -> ForecastResult:
    """Daily or monthly revenue forecast."""
    _set_cache(response, 600)
    result = service.get_revenue_forecast(granularity)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No revenue forecast available. Run the forecasting pipeline first.",
        )
    return result


@router.get("/products/{product_key}", response_model=ForecastResult)
@limiter.limit("60/minute")
def get_product_forecast(
    request: Request,
    response: Response,
    service: ForecastServiceDep,
    product_key: Annotated[int, Path(ge=1, description="Product surrogate key")],
) -> ForecastResult:
    """Product demand forecast (next 3 months)."""
    _set_cache(response, 600)
    result = service.get_product_forecast(product_key)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No forecast available for this product.",
        )
    return result


@router.get("/summary", response_model=ForecastSummary)
@limiter.limit("60/minute")
def get_forecast_summary(
    request: Request,
    response: Response,
    service: ForecastServiceDep,
) -> ForecastSummary:
    """Forecast overview — accuracy, key predictions, top movers."""
    _set_cache(response, 600)
    return service.get_forecast_summary()


@router.get("/customers/segments", response_model=list[CustomerSegment])
@limiter.limit("60/minute")
def get_customer_segments(
    request: Request,
    response: Response,
    service: ForecastServiceDep,
    segment: Annotated[str | None, Query(max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[CustomerSegment]:
    """Customer RFM segments from the feature store."""
    _set_cache(response, 120)
    return service.get_customer_segments(segment=segment, limit=limit)
