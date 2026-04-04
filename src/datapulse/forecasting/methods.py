"""Forecasting algorithms — Holt-Winters, SMA, Seasonal Naive.

Pure functions with no database or caching logic. Each returns a list of
ForecastPoint with point estimates and confidence intervals.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from datapulse.forecasting.models import ForecastAccuracy, ForecastPoint
from datapulse.logging import get_logger

log = get_logger(__name__)


# Confidence z-score lookup table
Z_TABLE: dict[float, float] = {
    0.80: 1.2816,
    0.90: 1.6449,
    0.95: 1.9600,
    0.99: 2.5758,
}


def _z_for_confidence(confidence: float) -> float:
    """Return z-score for a given confidence level, defaulting to 80%."""
    return Z_TABLE.get(confidence, Z_TABLE.get(0.80, 1.2816))


def select_method(series_length: int, seasonal_periods: int) -> str:
    """Pick the best forecasting method based on available data.

    Holt-Winters needs at least 2 full seasonal cycles to estimate
    seasonal components reliably.
    """
    if series_length >= 2 * seasonal_periods:
        return "holt_winters"
    if series_length >= seasonal_periods:
        return "seasonal_naive"
    return "sma"


def select_best_method(
    series: list[float],
    horizon: int,
    seasonal_periods: int,
    *,
    monthly: bool = False,
) -> tuple[str, ForecastAccuracy]:
    """Run all eligible methods on holdout, return (best_method, accuracy).

    Instead of picking based on series length alone, this function backtests
    all eligible methods and picks the one with the lowest MAPE.
    """
    candidates = ["sma"]
    n = len(series)
    if n >= seasonal_periods:
        candidates.append("seasonal_naive")
    if n >= 2 * seasonal_periods:
        candidates.append("holt_winters")

    bt_horizon = min(horizon, max(n // 4, 1))
    best_method = "sma"
    best_mape = Decimal("999999")
    best_acc = backtest(series, bt_horizon, seasonal_periods, "sma", monthly=monthly)

    for method in candidates:
        acc = backtest(series, bt_horizon, seasonal_periods, method, monthly=monthly)
        if acc.mape < best_mape:
            best_mape = acc.mape
            best_method = method
            best_acc = acc

    log.info(
        "forecast_method_selected",
        method=best_method,
        mape=float(best_mape),
        candidates=candidates,
    )
    return best_method, best_acc


def holt_winters_forecast(
    series: list[float],
    horizon: int,
    seasonal_periods: int,
    *,
    start_date: date | None = None,
    monthly: bool = False,
    confidence: float = 0.80,
) -> list[ForecastPoint]:
    """Holt-Winters exponential smoothing with additive seasonality.

    Falls back to SMA if statsmodels fitting fails (e.g., convergence error).
    """
    if len(series) < 2 * seasonal_periods:
        return sma_forecast(series, horizon, start_date=start_date, monthly=monthly)

    try:
        arr = np.array(series, dtype=np.float64)
        # Clamp near-zero values to avoid log issues with multiplicative
        arr = np.maximum(arr, 0.01)

        model = ExponentialSmoothing(
            arr,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_periods,
        )
        fit = model.fit(optimized=True)
        forecast_values = fit.forecast(horizon)

        # Confidence interval via residual standard error
        residuals = fit.resid
        std_err = float(np.std(residuals))
        z = _z_for_confidence(confidence)

    except Exception:
        log.warning("holt_winters_fallback_to_sma", reason="fit_failed")
        return sma_forecast(series, horizon, start_date=start_date, monthly=monthly)

    points: list[ForecastPoint] = []
    for i in range(horizon):
        val = max(float(forecast_values[i]), 0.0)
        margin = z * std_err * math.sqrt(1 + i / len(series))
        period = _make_period(start_date, i, monthly=monthly)
        points.append(
            ForecastPoint(
                period=period,
                value=Decimal(str(round(val, 2))),
                lower_bound=Decimal(str(round(max(val - margin, 0.0), 2))),
                upper_bound=Decimal(str(round(val + margin, 2))),
            )
        )
    return points


def sma_forecast(
    series: list[float],
    horizon: int,
    window: int = 30,
    *,
    start_date: date | None = None,
    monthly: bool = False,
    confidence: float = 0.80,
) -> list[ForecastPoint]:
    """Simple Moving Average forecast with expanding standard deviation bounds."""
    if not series:
        return []

    effective_window = min(window, len(series))
    tail = series[-effective_window:]
    mean_val = sum(tail) / len(tail)
    std_val = (sum((x - mean_val) ** 2 for x in tail) / len(tail)) ** 0.5
    z = _z_for_confidence(confidence)

    points: list[ForecastPoint] = []
    for i in range(horizon):
        margin = z * std_val * math.sqrt(1 + i / max(len(tail), 1))
        period = _make_period(start_date, i, monthly=monthly)
        points.append(
            ForecastPoint(
                period=period,
                value=Decimal(str(round(max(mean_val, 0.0), 2))),
                lower_bound=Decimal(str(round(max(mean_val - margin, 0.0), 2))),
                upper_bound=Decimal(str(round(mean_val + margin, 2))),
            )
        )
    return points


def seasonal_naive_forecast(
    series: list[float],
    horizon: int,
    seasonal_periods: int,
    *,
    start_date: date | None = None,
    monthly: bool = False,
    confidence: float = 0.80,
) -> list[ForecastPoint]:
    """Repeat the last full seasonal cycle as the forecast.

    The simplest seasonal baseline: next Monday = last Monday, next January = last January.
    """
    if len(series) < seasonal_periods:
        return sma_forecast(series, horizon, start_date=start_date, monthly=monthly)

    last_cycle = series[-seasonal_periods:]
    # Compute cycle-level standard deviation for confidence bounds
    if len(series) >= 2 * seasonal_periods:
        prev_cycle = series[-2 * seasonal_periods : -seasonal_periods]
        diffs = [abs(a - b) for a, b in zip(last_cycle, prev_cycle, strict=True)]
        std_val = (sum(d**2 for d in diffs) / len(diffs)) ** 0.5
    else:
        std_val = (
            sum((x - sum(last_cycle) / len(last_cycle)) ** 2 for x in last_cycle) / len(last_cycle)
        ) ** 0.5

    z = _z_for_confidence(confidence)
    points: list[ForecastPoint] = []
    for i in range(horizon):
        val = max(last_cycle[i % seasonal_periods], 0.0)
        margin = z * std_val
        period = _make_period(start_date, i, monthly=monthly)
        points.append(
            ForecastPoint(
                period=period,
                value=Decimal(str(round(val, 2))),
                lower_bound=Decimal(str(round(max(val - margin, 0.0), 2))),
                upper_bound=Decimal(str(round(val + margin, 2))),
            )
        )
    return points


def backtest(
    series: list[float],
    horizon: int,
    seasonal_periods: int,
    method: str,
    *,
    monthly: bool = False,
) -> ForecastAccuracy:
    """Train on series[:-horizon], predict horizon periods, compare to actuals.

    Returns MAPE, MAE, RMSE, and coverage (% of actuals within bounds).
    """
    if len(series) <= horizon:
        return ForecastAccuracy(
            mape=Decimal("0"), mae=Decimal("0"), rmse=Decimal("0"), coverage=Decimal("0")
        )

    train = series[:-horizon]
    actuals = series[-horizon:]

    if method == "holt_winters":
        points = holt_winters_forecast(train, horizon, seasonal_periods, monthly=monthly)
    elif method == "seasonal_naive":
        points = seasonal_naive_forecast(train, horizon, seasonal_periods, monthly=monthly)
    else:
        points = sma_forecast(train, horizon, monthly=monthly)

    if not points:
        return ForecastAccuracy(
            mape=Decimal("0"), mae=Decimal("0"), rmse=Decimal("0"), coverage=Decimal("0")
        )

    errors: list[float] = []
    abs_errors: list[float] = []
    sq_errors: list[float] = []
    within_bounds = 0

    for actual, point in zip(actuals, points, strict=False):
        predicted = float(point.value)
        ae = abs(actual - predicted)
        abs_errors.append(ae)
        sq_errors.append(ae**2)
        if actual != 0:
            errors.append(ae / abs(actual))
        lb = float(point.lower_bound)
        ub = float(point.upper_bound)
        if lb <= actual <= ub:
            within_bounds += 1

    n = len(abs_errors)
    mape = sum(errors) / len(errors) * 100 if errors else 0.0
    mae = sum(abs_errors) / n
    rmse = (sum(sq_errors) / n) ** 0.5
    coverage = within_bounds / n * 100

    return ForecastAccuracy(
        mape=Decimal(str(round(mape, 2))),
        mae=Decimal(str(round(mae, 2))),
        rmse=Decimal(str(round(rmse, 2))),
        coverage=Decimal(str(round(coverage, 2))),
    )


# -- helpers ------------------------------------------------------------------


def _make_period(start_date: date | None, offset: int, *, monthly: bool) -> str:
    """Generate period string for the i-th forecast step."""
    if start_date is None:
        start_date = date.today()

    if monthly:
        # Advance by months
        month = start_date.month + offset
        year = start_date.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        return f"{year}-{month:02d}"
    return str(start_date + timedelta(days=offset))


METHOD_MAP: dict[str, Callable[..., list[ForecastPoint]]] = {
    "holt_winters": holt_winters_forecast,
    "seasonal_naive": seasonal_naive_forecast,
    "sma": sma_forecast,
}
