"""Tests for forecast auto-selection by accuracy."""

from decimal import Decimal

from datapulse.forecasting.methods import (
    Z_TABLE,
    _z_for_confidence,
    select_best_method,
    select_method,
)


class TestZTable:
    def test_80_percent(self):
        assert Z_TABLE[0.80] == 1.2816

    def test_95_percent(self):
        assert Z_TABLE[0.95] == 1.9600

    def test_z_for_confidence_default(self):
        assert _z_for_confidence(0.80) == 1.2816

    def test_z_for_confidence_unknown(self):
        # Unknown confidence level falls back to 80%
        assert _z_for_confidence(0.75) == 1.2816


class TestSelectMethod:
    """Original method selection still works."""

    def test_holt_winters_for_long_series(self):
        assert select_method(30, 7) == "holt_winters"

    def test_seasonal_naive_for_medium_series(self):
        assert select_method(10, 7) == "seasonal_naive"

    def test_sma_for_short_series(self):
        assert select_method(5, 7) == "sma"


class TestSelectBestMethod:
    def test_returns_tuple(self):
        series = list(range(1, 31))  # 30 data points
        method, acc = select_best_method([float(x) for x in series], 7, 7)
        assert method in ("sma", "seasonal_naive", "holt_winters")
        assert hasattr(acc, "mape")

    def test_short_series_only_sma(self):
        series = [100.0, 110.0, 105.0]
        method, acc = select_best_method(series, 1, 7)
        assert method == "sma"

    def test_medium_series_includes_seasonal(self):
        series = [float(i % 7 * 10 + 100) for i in range(10)]
        method, acc = select_best_method(series, 3, 7)
        assert method in ("sma", "seasonal_naive")

    def test_long_series_includes_all_candidates(self):
        # Generate a seasonal series with noise
        import random

        random.seed(42)
        series = [float(100 + 20 * (i % 7) + random.gauss(0, 5)) for i in range(50)]
        method, acc = select_best_method(series, 7, 7)
        assert method in ("sma", "seasonal_naive", "holt_winters")
        assert acc.mape >= Decimal("0")
