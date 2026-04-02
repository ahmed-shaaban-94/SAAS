"""Tests for datapulse.forecasting.repository — all methods with mocked session."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.forecasting.models import (
    ForecastAccuracy,
    ForecastPoint,
    ForecastResult,
)
from datapulse.forecasting.repository import ForecastingRepository


@pytest.fixture()
def repo():
    session = MagicMock()
    return ForecastingRepository(session), session


class TestGetDailyRevenueSeries:
    def test_returns_date_float_tuples(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (date(2025, 1, 1), Decimal("1000.50")),
            (date(2025, 1, 2), Decimal("2000.75")),
        ]
        result = r.get_daily_revenue_series(lookback_days=30)
        assert len(result) == 2
        assert result[0] == (date(2025, 1, 1), 1000.50)
        assert isinstance(result[0][1], float)

    def test_empty_series(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = []
        result = r.get_daily_revenue_series()
        assert result == []


class TestGetMonthlyRevenueSeries:
    def test_returns_period_float_tuples(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            ("2025-01", Decimal("50000")),
            ("2025-02", Decimal("60000")),
        ]
        result = r.get_monthly_revenue_series()
        assert len(result) == 2
        assert result[0] == ("2025-01", 50000.0)


class TestGetProductMonthlySeries:
    def test_returns_series_for_product(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            ("2025-01", Decimal("5000")),
        ]
        result = r.get_product_monthly_series(product_key=42)
        assert len(result) == 1
        assert result[0] == ("2025-01", 5000.0)


class TestGetTopProductsByRevenue:
    def test_returns_key_name_tuples(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (1, "Aspirin"),
            (2, "Paracetamol"),
        ]
        result = r.get_top_products_by_revenue(limit=2)
        assert result == [(1, "Aspirin"), (2, "Paracetamol")]


class TestGetCustomerSegments:
    def test_without_segment_filter(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (
                1,
                "C001",
                "Customer A",
                "Champions",
                5,
                5,
                5,
                10,
                50,
                Decimal("100000"),
                Decimal("2000"),
                Decimal("0.05"),
            ),
        ]
        result = r.get_customer_segments(limit=10)
        assert len(result) == 1
        assert result[0].rfm_segment == "Champions"
        assert result[0].monetary == Decimal("100000")

    def test_with_segment_filter(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (2, "C002", "Customer B", "At Risk", 2, 1, 3, 90, 5, Decimal("5000"), None, None),
        ]
        result = r.get_customer_segments(segment="At Risk", limit=5)
        assert len(result) == 1
        assert result[0].avg_basket_size == Decimal("0")
        assert result[0].return_rate == Decimal("0")


class TestSaveForecasts:
    def test_empty_results_returns_zero(self, repo):
        r, _ = repo
        count = r.save_forecasts([], run_at=datetime.now())
        assert count == 0

    def test_saves_rows_and_returns_count(self, repo):
        r, session = repo
        results = [
            ForecastResult(
                entity_type="revenue",
                entity_key=None,
                method="holt_winters",
                horizon=2,
                granularity="daily",
                points=[
                    ForecastPoint(
                        period="2026-04-01",
                        value=Decimal("1000"),
                        lower_bound=Decimal("900"),
                        upper_bound=Decimal("1100"),
                    ),
                    ForecastPoint(
                        period="2026-04-02",
                        value=Decimal("1100"),
                        lower_bound=Decimal("1000"),
                        upper_bound=Decimal("1200"),
                    ),
                ],
                accuracy_metrics=ForecastAccuracy(
                    mape=Decimal("5.2"),
                    mae=Decimal("50"),
                    rmse=Decimal("60"),
                    coverage=Decimal("0.95"),
                ),
            ),
        ]
        count = r.save_forecasts(results, run_at=datetime(2026, 4, 1))
        assert count == 2
        assert session.execute.call_count == 2
        session.flush.assert_called_once()

    def test_saves_without_accuracy(self, repo):
        r, session = repo
        results = [
            ForecastResult(
                entity_type="product",
                entity_key=42,
                method="sma",
                horizon=1,
                granularity="monthly",
                points=[
                    ForecastPoint(
                        period="2026-05",
                        value=Decimal("500"),
                        lower_bound=Decimal("400"),
                        upper_bound=Decimal("600"),
                    ),
                ],
                accuracy_metrics=None,
            ),
        ]
        count = r.save_forecasts(results, run_at=datetime(2026, 4, 1))
        assert count == 1


class TestGetForecast:
    def test_returns_none_when_no_rows(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = []
        result = r.get_forecast("revenue", "daily")
        assert result is None

    def test_returns_forecast_with_accuracy(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (
                date(2026, 4, 1),
                Decimal("1000"),
                Decimal("900"),
                Decimal("1100"),
                "holt_winters",
                Decimal("5.2"),
                Decimal("50"),
                Decimal("60"),
                datetime(2026, 4, 1),
            ),
            (
                date(2026, 4, 2),
                Decimal("1100"),
                Decimal("1000"),
                Decimal("1200"),
                "holt_winters",
                Decimal("5.2"),
                Decimal("50"),
                Decimal("60"),
                datetime(2026, 4, 1),
            ),
        ]
        result = r.get_forecast("revenue", "daily")
        assert result is not None
        assert result.entity_type == "revenue"
        assert result.method == "holt_winters"
        assert len(result.points) == 2
        assert result.accuracy_metrics is not None
        assert result.accuracy_metrics.mape == Decimal("5.2")

    def test_returns_forecast_without_accuracy(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (
                date(2026, 4, 1),
                Decimal("1000"),
                Decimal("900"),
                Decimal("1100"),
                "sma",
                None,
                None,
                None,
                datetime(2026, 4, 1),
            ),
        ]
        result = r.get_forecast("revenue", "daily")
        assert result is not None
        assert result.accuracy_metrics is None

    def test_with_entity_key(self, repo):
        r, session = repo
        session.execute.return_value.fetchall.return_value = [
            (
                date(2026, 5, 1),
                Decimal("500"),
                Decimal("400"),
                Decimal("600"),
                "sma",
                None,
                None,
                None,
                datetime(2026, 4, 1),
            ),
        ]
        result = r.get_forecast("product", "monthly", entity_key=42)
        assert result is not None
        assert result.entity_key == 42


class TestGetForecastSummaryData:
    def test_returns_summary_dict(self, repo):
        r, session = repo
        # Mock 5 consecutive scalar/fetchall calls
        session.execute.return_value.scalar.side_effect = [
            datetime(2026, 4, 1),  # last_run
            Decimal("30000"),  # next_30d
            Decimal("90000"),  # next_3m
            Decimal("5.5"),  # mape
        ]
        session.execute.return_value.fetchall.side_effect = [
            [(1, "Drug A", Decimal("15.2"))],  # growing
            [(2, "Drug B", Decimal("-8.3"))],  # declining
        ]

        # Need to handle multiple execute calls with different return values
        scalar_values = [datetime(2026, 4, 1), Decimal("30000"), Decimal("90000"), Decimal("5.5")]
        fetchall_values = [
            [(1, "Drug A", Decimal("15.2"))],
            [(2, "Drug B", Decimal("-8.3"))],
        ]

        scalar_idx = [0]

        def mock_execute(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.scalar.side_effect = lambda: (
                scalar_values[scalar_idx[0]].__class__(scalar_values[scalar_idx[0]])
                if scalar_idx[0] < len(scalar_values)
                else None
            )
            return mock_result

        # Simpler approach: use side_effect with multiple mock results
        results = []
        for val in scalar_values:
            m = MagicMock()
            m.scalar.return_value = val
            results.append(m)
        for val in fetchall_values:
            m = MagicMock()
            m.fetchall.return_value = val
            results.append(m)

        session.execute.side_effect = results

        data = r.get_forecast_summary_data()
        assert data["last_run_at"] == datetime(2026, 4, 1)
        assert data["next_30d_revenue"] == Decimal("30000")
        assert data["next_3m_revenue"] == Decimal("90000")
        assert data["mape"] == Decimal("5.5")
        assert len(data["growing"]) == 1
        assert len(data["declining"]) == 1
