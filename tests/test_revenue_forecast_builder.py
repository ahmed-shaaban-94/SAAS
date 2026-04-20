"""Unit tests for the ``/analytics/revenue-forecast`` composer (#504)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from datapulse.analytics.models import TimeSeriesPoint
from datapulse.analytics.revenue_forecast_builder import compose_revenue_forecast
from datapulse.forecasting.models import ForecastAccuracy, ForecastPoint, ForecastResult
from datapulse.targets.models import TargetSummary, TargetVsActual

# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


def _actual(*values: str) -> list[TimeSeriesPoint]:
    return [
        TimeSeriesPoint(period=f"2026-04-{i + 1:02d}", value=Decimal(v))
        for i, v in enumerate(values)
    ]


def _forecast(
    *,
    points: list[tuple[str, str, str, str]] | None = None,
    mape: str | None = "10",
) -> ForecastResult:
    return ForecastResult(
        entity_type="revenue",
        method="holt_winters",
        horizon=len(points or []),
        granularity="daily",
        points=[
            ForecastPoint(
                period=p,
                value=Decimal(v),
                lower_bound=Decimal(lb),
                upper_bound=Decimal(ub),
            )
            for p, v, lb, ub in (points or [])
        ],
        accuracy_metrics=ForecastAccuracy(
            mape=Decimal(mape),
            mae=Decimal("1000"),
            rmse=Decimal("1500"),
            coverage=Decimal("95"),
        )
        if mape is not None
        else None,
    )


def _target_summary(ytd_target: str, ytd_actual: str) -> TargetSummary:
    return TargetSummary(
        monthly_targets=[
            TargetVsActual(
                period="2026-01",
                target_value=Decimal("100000"),
                actual_value=Decimal("95000"),
                variance=Decimal("-5000"),
                achievement_pct=Decimal("95"),
            ),
        ],
        ytd_target=Decimal(ytd_target),
        ytd_actual=Decimal(ytd_actual),
        ytd_achievement_pct=Decimal("0"),
    )


_TODAY = date(2026, 4, 20)


# ────────────────────────────────────────────────────────────────────────
# Period validation
# ────────────────────────────────────────────────────────────────────────


def test_invalid_period_raises_value_error():
    with pytest.raises(ValueError, match="Invalid period"):
        compose_revenue_forecast(
            actual=[],
            forecast=None,
            target_summary=None,
            today=_TODAY,
            period="decade",  # not supported
            this_period_total=Decimal("0"),
        )


@pytest.mark.parametrize("period", ["day", "week", "month", "quarter", "ytd"])
def test_supported_periods_accepted(period):
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period=period,
        this_period_total=Decimal("0"),
    )
    assert result.period == period


# ────────────────────────────────────────────────────────────────────────
# Forecast projection
# ────────────────────────────────────────────────────────────────────────


def test_forecast_points_map_to_band_shape():
    forecast = _forecast(points=[("2026-04-21", "150000", "140000", "160000")])
    result = compose_revenue_forecast(
        actual=[],
        forecast=forecast,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert len(result.forecast) == 1
    band = result.forecast[0]
    assert band.date == "2026-04-21"
    assert band.value == Decimal("150000")
    assert band.ci_low == Decimal("140000")
    assert band.ci_high == Decimal("160000")


def test_no_forecast_returns_empty_band():
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert result.forecast == []
    assert result.stats.confidence is None


# ────────────────────────────────────────────────────────────────────────
# Target projection
# ────────────────────────────────────────────────────────────────────────


def test_target_none_when_summary_missing():
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert result.target is None


def test_target_none_when_ytd_target_is_zero():
    summary = _target_summary(ytd_target="0", ytd_actual="50000")
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=summary,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert result.target is None


def test_target_status_on_track_within_tolerance():
    # 95% of target → on_track (within 10% band)
    summary = _target_summary(ytd_target="1000000", ytd_actual="950000")
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=summary,
        today=_TODAY,
        period="ytd",
        this_period_total=Decimal("950000"),
    )
    assert result.target is not None
    assert result.target.status == "on_track"
    assert result.target.value == Decimal("1000000")


def test_target_status_behind_below_tolerance():
    summary = _target_summary(ytd_target="1000000", ytd_actual="800000")
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=summary,
        today=_TODAY,
        period="ytd",
        this_period_total=Decimal("800000"),
    )
    assert result.target is not None
    assert result.target.status == "behind"


def test_target_status_ahead_above_tolerance():
    summary = _target_summary(ytd_target="1000000", ytd_actual="1200000")
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=summary,
        today=_TODAY,
        period="ytd",
        this_period_total=Decimal("1200000"),
    )
    assert result.target is not None
    assert result.target.status == "ahead"


def test_target_period_end_defaults_to_year_end():
    summary = _target_summary(ytd_target="1000000", ytd_actual="500000")
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=summary,
        today=_TODAY,
        period="ytd",
        this_period_total=Decimal("500000"),
    )
    assert result.target is not None
    assert result.target.period_end == date(2026, 12, 31)


def test_target_period_end_override_respected():
    summary = _target_summary(ytd_target="100000", ytd_actual="50000")
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=summary,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("50000"),
        target_period_end=date(2026, 4, 30),
    )
    assert result.target is not None
    assert result.target.period_end == date(2026, 4, 30)


# ────────────────────────────────────────────────────────────────────────
# Stats
# ────────────────────────────────────────────────────────────────────────


def test_stats_delta_pct_computed_from_previous_period():
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("1200000"),
        previous_period_total=Decimal("1000000"),
    )
    assert result.stats.delta_pct == Decimal("20.0")


def test_stats_delta_pct_none_when_previous_zero():
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("1000000"),
        previous_period_total=Decimal("0"),
    )
    assert result.stats.delta_pct is None


def test_stats_confidence_mirrors_mape():
    # MAPE 10 → confidence 90
    forecast = _forecast(points=[("2026-04-21", "150000", "140000", "160000")], mape="10")
    result = compose_revenue_forecast(
        actual=[],
        forecast=forecast,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert result.stats.confidence == 90


def test_stats_confidence_clamped_at_zero_for_bad_mape():
    """A MAPE > 100 must not produce negative confidence."""
    forecast = _forecast(points=[("2026-04-21", "150000", "0", "0")], mape="150")
    result = compose_revenue_forecast(
        actual=[],
        forecast=forecast,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert result.stats.confidence == 0


def test_stats_confidence_none_when_forecast_lacks_accuracy():
    forecast = _forecast(points=[("2026-04-21", "150000", "140000", "160000")], mape=None)
    result = compose_revenue_forecast(
        actual=[],
        forecast=forecast,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("0"),
    )
    assert result.stats.confidence is None


# ────────────────────────────────────────────────────────────────────────
# Passthrough fields
# ────────────────────────────────────────────────────────────────────────


def test_actual_passthrough_unchanged():
    actual = _actual("100", "200", "150")
    result = compose_revenue_forecast(
        actual=actual,
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period="month",
        this_period_total=Decimal("450"),
    )
    assert result.actual == actual


def test_today_and_period_echoed_back():
    result = compose_revenue_forecast(
        actual=[],
        forecast=None,
        target_summary=None,
        today=_TODAY,
        period="quarter",
        this_period_total=Decimal("0"),
    )
    assert result.today == _TODAY
    assert result.period == "quarter"
