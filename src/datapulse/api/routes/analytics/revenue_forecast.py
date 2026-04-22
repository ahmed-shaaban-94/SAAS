"""Composite revenue-forecast endpoint (#504)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.analytics.models import (
    AnalyticsFilter,
    DateRange,
    RevenueForecast,
)
from datapulse.analytics.revenue_forecast_builder import compose_revenue_forecast
from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.deps import get_forecasting_service, get_targets_service
from datapulse.api.limiter import limiter
from datapulse.api.routes.analytics._shared import ServiceDep
from datapulse.forecasting.service import ForecastingService
from datapulse.logging import get_logger
from datapulse.targets.service import TargetsService

log = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _period_window(period: str, today: date) -> tuple[date, date, date, date]:
    """Return (start, end, prev_start, prev_end) windows for ``period``.

    Keeps the mapping in one place so the route + tests agree. ``today``
    is always clipped into the window (the chart rule is "show up to
    today", not "end of calendar window").
    """
    if period == "day":
        return today, today, today - timedelta(days=1), today - timedelta(days=1)
    if period == "week":
        start = today - timedelta(days=today.weekday())
        prev_start = start - timedelta(days=7)
        return start, today, prev_start, prev_start + timedelta(days=6)
    if period == "month":
        start = today.replace(day=1)
        # Previous month window — same length, shifted back.
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        return start, today, prev_start, prev_end
    if period == "quarter":
        quarter_idx = (today.month - 1) // 3
        start = today.replace(month=quarter_idx * 3 + 1, day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(month=((quarter_idx - 1) % 4) * 3 + 1, day=1)
        return start, today, prev_start, prev_end
    # ytd
    start = date(today.year, 1, 1)
    prev_start = date(today.year - 1, 1, 1)
    prev_end = date(today.year - 1, today.month, today.day)
    return start, today, prev_start, prev_end


@router.get("/revenue-forecast", response_model=RevenueForecast)
@limiter.limit("60/minute")
def get_revenue_forecast(
    request: Request,
    response: Response,
    analytics: ServiceDep,
    forecasting: Annotated[ForecastingService, Depends(get_forecasting_service)],
    targets: Annotated[TargetsService, Depends(get_targets_service)],
    period: Annotated[str, Query(pattern="^(day|week|month|quarter|ytd)$")] = "month",
    target_date: Annotated[date | None, Query()] = None,
) -> RevenueForecast:
    """Composite actual + forecast + target + stats for the dashboard chart.

    Single-call replacement for three upstream hooks (``/trends/daily``,
    ``/forecasting/revenue``, ``/targets/summary``) — saves cache
    round-trips and eliminates loading-state flicker on the new
    dashboard design (#504).
    """
    set_cache_headers(response, 300)

    today = target_date or datetime.now(UTC).date()
    start, end, prev_start, prev_end = _period_window(period, today)

    # Historical actual — daily trend inside the current window.
    filters = AnalyticsFilter(date_range=DateRange(start_date=start, end_date=end))
    daily = analytics.get_daily_trend(filters)
    prev_filters = AnalyticsFilter(date_range=DateRange(start_date=prev_start, end_date=prev_end))
    prev_daily = analytics.get_daily_trend(prev_filters)

    # Forecast — fails silently if not yet generated for this tenant.
    forecast = None
    try:
        forecast = forecasting.get_revenue_forecast("daily")
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("revenue_forecast_fetch_failed", error=str(exc))

    # Target — RLS-scoped via the injected TargetsService.
    target_summary = None
    try:
        target_summary = targets.get_target_summary(today.year)
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("revenue_forecast_target_failed", error=str(exc))

    this_period_total = Decimal(str(daily.total)) if daily.total is not None else Decimal("0")
    prev_period_total = (
        Decimal(str(prev_daily.total)) if prev_daily.total is not None else Decimal("0")
    )

    return compose_revenue_forecast(
        actual=list(daily.points),
        forecast=forecast,
        target_summary=target_summary,
        today=today,
        period=period,
        this_period_total=this_period_total,
        previous_period_total=prev_period_total,
    )
