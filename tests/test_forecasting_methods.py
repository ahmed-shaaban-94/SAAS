"""Tests for forecasting algorithms (methods.py)."""

from __future__ import annotations

from datetime import date

from datapulse.forecasting.methods import (
    backtest,
    holt_winters_forecast,
    seasonal_naive_forecast,
    select_method,
    sma_forecast,
)


class TestSelectMethod:
    """Method selection based on series length."""

    def test_holt_winters_when_enough_data(self):
        assert select_method(14, 7) == "holt_winters"
        assert select_method(24, 12) == "holt_winters"
        assert select_method(100, 7) == "holt_winters"

    def test_seasonal_naive_when_moderate_data(self):
        assert select_method(7, 7) == "seasonal_naive"
        assert select_method(13, 7) == "seasonal_naive"
        assert select_method(12, 12) == "seasonal_naive"

    def test_sma_when_sparse_data(self):
        assert select_method(6, 7) == "sma"
        assert select_method(3, 12) == "sma"
        assert select_method(1, 7) == "sma"


class TestSMAForecast:
    """Simple Moving Average forecasting."""

    def test_constant_series(self):
        series = [100.0] * 30
        points = sma_forecast(series, horizon=5, start_date=date(2026, 1, 1))
        assert len(points) == 5
        for p in points:
            assert float(p.value) == 100.0
            assert float(p.lower_bound) <= float(p.value)
            assert float(p.upper_bound) >= float(p.value)

    def test_period_format(self):
        points = sma_forecast([100.0] * 10, horizon=3, start_date=date(2026, 4, 1))
        assert points[0].period == "2026-04-01"
        assert points[1].period == "2026-04-02"
        assert points[2].period == "2026-04-03"

    def test_monthly_period_format(self):
        points = sma_forecast([100.0] * 10, horizon=3, start_date=date(2026, 4, 1), monthly=True)
        assert points[0].period == "2026-04"
        assert points[1].period == "2026-05"
        assert points[2].period == "2026-06"

    def test_empty_series(self):
        assert sma_forecast([], horizon=5) == []

    def test_values_non_negative(self):
        series = [50.0, 30.0, 20.0, 10.0, 5.0]
        points = sma_forecast(series, horizon=10)
        for p in points:
            assert float(p.value) >= 0
            assert float(p.lower_bound) >= 0

    def test_window_smaller_than_series(self):
        series = [100.0] * 5
        points = sma_forecast(series, horizon=3, window=30)
        assert len(points) == 3


class TestSeasonalNaiveForecast:
    """Seasonal Naive forecasting."""

    def test_repeats_last_cycle(self):
        # Weekly pattern: Mon-Sun
        cycle = [100, 120, 130, 140, 80, 60, 50]
        series = cycle * 3  # 3 weeks
        points = seasonal_naive_forecast(
            series, horizon=7, seasonal_periods=7, start_date=date(2026, 1, 1)
        )
        assert len(points) == 7
        for i, p in enumerate(points):
            assert float(p.value) == cycle[i]

    def test_wraps_around_for_longer_horizon(self):
        cycle = [100, 200, 300]
        series = cycle * 3
        points = seasonal_naive_forecast(series, horizon=6, seasonal_periods=3)
        values = [float(p.value) for p in points]
        assert values == [100, 200, 300, 100, 200, 300]

    def test_falls_back_to_sma_when_insufficient(self):
        series = [100, 200, 300]  # less than seasonal_periods=7
        points = seasonal_naive_forecast(series, horizon=3, seasonal_periods=7)
        assert len(points) == 3  # fell back to SMA


class TestHoltWintersForecast:
    """Holt-Winters exponential smoothing."""

    def test_produces_correct_horizon(self):
        # Generate 4 weeks of data with weekly seasonality
        base = [100, 120, 130, 140, 80, 60, 50]
        series = []
        for i in range(4):
            series.extend([v + i * 10 for v in base])

        points = holt_winters_forecast(
            series, horizon=7, seasonal_periods=7, start_date=date(2026, 1, 1)
        )
        assert len(points) == 7

    def test_confidence_intervals(self):
        base = [100, 120, 130, 140, 80, 60, 50]
        series = base * 4
        points = holt_winters_forecast(series, horizon=7, seasonal_periods=7)
        for p in points:
            assert float(p.lower_bound) <= float(p.value)
            assert float(p.upper_bound) >= float(p.value)

    def test_falls_back_on_short_series(self):
        series = [100, 200, 300]  # too short for seasonal_periods=7
        points = holt_winters_forecast(series, horizon=5, seasonal_periods=7)
        assert len(points) == 5  # fell back to SMA

    def test_values_non_negative(self):
        base = [100, 120, 130, 140, 80, 60, 50]
        series = base * 4
        points = holt_winters_forecast(series, horizon=14, seasonal_periods=7)
        for p in points:
            assert float(p.value) >= 0
            assert float(p.lower_bound) >= 0


class TestBacktest:
    """Backtesting accuracy metrics."""

    def test_perfect_prediction(self):
        # Constant series — SMA should predict perfectly
        series = [100.0] * 40
        accuracy = backtest(series, horizon=5, seasonal_periods=7, method="sma")
        assert float(accuracy.mape) == 0.0
        assert float(accuracy.mae) == 0.0
        assert float(accuracy.coverage) == 100.0

    def test_returns_accuracy_object(self):
        series = [float(x) for x in range(50)]
        accuracy = backtest(series, horizon=5, seasonal_periods=7, method="sma")
        assert hasattr(accuracy, "mape")
        assert hasattr(accuracy, "mae")
        assert hasattr(accuracy, "rmse")
        assert hasattr(accuracy, "coverage")

    def test_handles_short_series(self):
        series = [100.0, 200.0]
        accuracy = backtest(series, horizon=5, seasonal_periods=7, method="sma")
        # Should not crash — returns zero accuracy
        assert float(accuracy.mape) == 0.0

    def test_seasonal_naive_backtest(self):
        cycle = [100, 200, 300, 400, 500, 600, 700]
        series = cycle * 4
        accuracy = backtest(series, horizon=7, seasonal_periods=7, method="seasonal_naive")
        # Perfect match expected (repeating cycle)
        assert float(accuracy.mape) == 0.0
