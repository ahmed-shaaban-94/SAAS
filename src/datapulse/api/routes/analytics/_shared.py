"""Shared query params and helpers for analytics sub-routers."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.service import AnalyticsService
from datapulse.api.deps import get_analytics_service


class AnalyticsQueryParams(BaseModel):
    """Common query parameters shared across analytics endpoints."""

    start_date: date | None = None
    end_date: date | None = None
    category: Annotated[str | None, Field(max_length=100)] = None
    brand: Annotated[str | None, Field(max_length=100)] = None
    site_key: int | None = None
    staff_key: int | None = None
    limit: int = Field(default=10, ge=1, le=100)


def to_filter(params: AnalyticsQueryParams) -> AnalyticsFilter | None:
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
