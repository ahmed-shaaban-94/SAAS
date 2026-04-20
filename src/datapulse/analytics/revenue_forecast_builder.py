"""Pure composer for ``/analytics/revenue-forecast`` (#504).

Fans three upstream results — historical daily trend, forecast output,
and a target summary — into the single ``RevenueForecast`` shape the
dashboard chart expects. Kept dependency-free so every branch can be
unit-tested without the DB or forecasting engine.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from datapulse.analytics.models.revenue_forecast import (
    ForecastBandPoint,
    RevenueForecast,
    RevenueForecastStats,
    RevenueTarget,
)
from datapulse.analytics.models.shared import TimeSeriesPoint
from datapulse.forecasting.models import ForecastResult
from datapulse.targets.models import TargetSummary

_SUPPORTED_PERIODS: frozenset[str] = frozenset({"day", "week", "month", "quarter", "ytd"})


def _target_status(target_value: Decimal, actual_value: Decimal) -> str:
    """Derive ``on_track`` / ``behind`` / ``ahead`` vs the period target.

    Uses a 10% tolerance band around the target so tiny deviations don't
    flip the status every render. Zero target → ``unknown`` (no reference).
    """
    if target_value <= 0:
        return "unknown"
    ratio = actual_value / target_value
    if ratio >= Decimal("1.10"):
        return "ahead"
    if ratio < Decimal("0.90"):
        return "behind"
    return "on_track"


def _delta_pct(current: Decimal, previous: Decimal) -> Decimal | None:
    """Percentage change between two magnitudes, or ``None`` if undefined."""
    if previous <= 0:
        return None
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.1"))


def _mape_to_confidence(mape: Decimal | None) -> int | None:
    """Forecast MAPE → 0–100 confidence score.

    MAPE 0%  → 100 confidence
    MAPE 100% → 0 confidence
    Values outside [0, 100] are clamped.
    """
    if mape is None:
        return None
    value = Decimal("100") - mape
    if value < 0:
        return 0
    if value > 100:
        return 100
    return int(value)


def compose_revenue_forecast(
    *,
    actual: list[TimeSeriesPoint],
    forecast: ForecastResult | None,
    target_summary: TargetSummary | None,
    today: date,
    period: str,
    this_period_total: Decimal,
    previous_period_total: Decimal = Decimal("0"),
    target_period_end: date | None = None,
) -> RevenueForecast:
    """Compose the composite revenue-forecast response.

    Caller responsibilities:
    - ``actual`` is the historical daily trend up to and including ``today``
    - ``forecast`` is the latest stored daily forecast (or ``None`` if the
      tenant has no forecast yet — the response then omits the band)
    - ``target_summary`` is the YTD target payload; we pick the YTD
      target as the overlay reference. Absent → ``target`` is ``None``.
    - ``this_period_total`` is pre-computed to keep this function pure.
    """
    if period not in _SUPPORTED_PERIODS:
        raise ValueError(
            f"Invalid period '{period}'. Must be one of: {', '.join(sorted(_SUPPORTED_PERIODS))}"
        )

    forecast_points: list[ForecastBandPoint] = []
    confidence: int | None = None
    if forecast is not None:
        forecast_points = [
            ForecastBandPoint(
                date=p.period,
                value=p.value,
                ci_low=p.lower_bound,
                ci_high=p.upper_bound,
            )
            for p in forecast.points
        ]
        if forecast.accuracy_metrics is not None:
            confidence = _mape_to_confidence(forecast.accuracy_metrics.mape)

    target_row: RevenueTarget | None = None
    if target_summary is not None and target_summary.ytd_target > 0:
        target_row = RevenueTarget(
            period_end=target_period_end or date(today.year, 12, 31),
            value=Decimal(str(target_summary.ytd_target)),
            status=_target_status(
                Decimal(str(target_summary.ytd_target)),
                Decimal(str(target_summary.ytd_actual)),
            ),
        )

    stats = RevenueForecastStats(
        this_period_egp=this_period_total,
        delta_pct=_delta_pct(this_period_total, previous_period_total),
        confidence=confidence,
    )

    return RevenueForecast(
        actual=actual,
        forecast=forecast_points,
        target=target_row,
        today=today,
        period=period,
        stats=stats,
    )
