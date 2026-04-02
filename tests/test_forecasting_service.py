"""Tests for ForecastingService business logic."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from datapulse.forecasting.models import (
    ForecastPoint,
    ForecastResult,
    ForecastSummary,
)
from datapulse.forecasting.repository import ForecastingRepository
from datapulse.forecasting.service import ForecastingService


@pytest.fixture()
def mock_forecast_repo():
    return create_autospec(ForecastingRepository, instance=True)


@pytest.fixture()
def forecast_service(mock_forecast_repo):
    return ForecastingService(mock_forecast_repo)


class TestGetRevenueForecast:
    def test_returns_stored_forecast(self, forecast_service, mock_forecast_repo):
        expected = ForecastResult(
            entity_type="revenue",
            method="holt_winters",
            horizon=30,
            granularity="daily",
            points=[
                ForecastPoint(
                    period="2026-04-01",
                    value=Decimal("1000"),
                    lower_bound=Decimal("900"),
                    upper_bound=Decimal("1100"),
                )
            ],
        )
        mock_forecast_repo.get_forecast.return_value = expected
        result = forecast_service.get_revenue_forecast("daily")
        mock_forecast_repo.get_forecast.assert_called_once_with("revenue", "daily")
        assert result == expected

    def test_returns_none_when_no_forecast(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.get_forecast.return_value = None
        result = forecast_service.get_revenue_forecast("monthly")
        assert result is None


class TestGetProductForecast:
    def test_returns_product_forecast(self, forecast_service, mock_forecast_repo):
        expected = ForecastResult(
            entity_type="product",
            entity_key=42,
            method="sma",
            horizon=3,
            granularity="monthly",
            points=[],
        )
        mock_forecast_repo.get_forecast.return_value = expected
        forecast_service.get_product_forecast(42)
        mock_forecast_repo.get_forecast.assert_called_once_with(
            "product", "monthly", entity_key=42
        )


class TestRunAllForecasts:
    def test_runs_daily_and_monthly(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.get_daily_revenue_series.return_value = [
            (date(2026, 1, 1) + __import__("datetime").timedelta(days=i), 100.0 + i)
            for i in range(100)
        ]
        mock_forecast_repo.get_monthly_revenue_series.return_value = [
            (f"2024-{m:02d}", 10000.0 + m * 100) for m in range(1, 13)
        ] + [
            (f"2025-{m:02d}", 11000.0 + m * 100) for m in range(1, 13)
        ]
        mock_forecast_repo.get_top_products_by_revenue.return_value = []
        mock_forecast_repo.save_forecasts.return_value = 33

        stats = forecast_service.run_all_forecasts()
        assert "daily_revenue" in stats
        assert "monthly_revenue" in stats
        assert stats["products_forecasted"] == 0
        mock_forecast_repo.save_forecasts.assert_called_once()

    def test_handles_empty_series(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.get_daily_revenue_series.return_value = []
        mock_forecast_repo.get_monthly_revenue_series.return_value = []
        mock_forecast_repo.get_top_products_by_revenue.return_value = []
        mock_forecast_repo.save_forecasts.return_value = 0

        stats = forecast_service.run_all_forecasts()
        assert stats["products_forecasted"] == 0

    def test_forecasts_products(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.get_daily_revenue_series.return_value = []
        mock_forecast_repo.get_monthly_revenue_series.return_value = []
        mock_forecast_repo.get_top_products_by_revenue.return_value = [
            (1, "Drug A"),
            (2, "Drug B"),
        ]
        # Drug A has enough data, Drug B has too little
        mock_forecast_repo.get_product_monthly_series.side_effect = [
            [(f"2025-{m:02d}", 500.0 + m * 10) for m in range(1, 7)],  # 6 months
            [("2025-01", 100.0)],  # only 1 month - skipped (< 3)
        ]
        mock_forecast_repo.save_forecasts.return_value = 3

        stats = forecast_service.run_all_forecasts()
        assert stats["products_forecasted"] == 1


class TestGetForecastSummary:
    def test_returns_summary(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.get_forecast_summary_data.return_value = {
            "last_run_at": datetime(2026, 4, 1, 12, 0),
            "next_30d_revenue": Decimal("500000"),
            "next_3m_revenue": Decimal("1500000"),
            "mape": Decimal("4.5"),
            "growing": [
                {"product_key": 1, "drug_name": "Drug A", "change_pct": Decimal("15")},
            ],
            "declining": [],
        }
        mock_forecast_repo.get_daily_revenue_series.return_value = [
            (date(2026, 3, d), 15000.0) for d in range(1, 31)
        ]

        result = forecast_service.get_forecast_summary()
        assert isinstance(result, ForecastSummary)
        assert result.next_30d_revenue == Decimal("500000")
        assert len(result.top_growing_products) == 1
