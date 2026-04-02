"""Forecasting business logic layer with Redis caching."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from datapulse.cache_decorator import cached
from datapulse.forecasting.methods import (
    backtest,
    holt_winters_forecast,
    seasonal_naive_forecast,
    select_method,
    sma_forecast,
)
from datapulse.forecasting.models import (
    CustomerSegment,
    ForecastResult,
    ForecastSummary,
    ProductForecastSummary,
)
from datapulse.forecasting.repository import ForecastingRepository
from datapulse.logging import get_logger

log = get_logger(__name__)

_FORECAST_PREFIX = "datapulse:forecast"


class ForecastingService:
    """Orchestrates forecasting jobs and serves cached results."""

    def __init__(self, repo: ForecastingRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Read endpoints (cached)
    # ------------------------------------------------------------------

    @cached(ttl=600, prefix=_FORECAST_PREFIX)
    def get_revenue_forecast(self, granularity: str = "daily") -> ForecastResult | None:
        """Return the latest stored daily/monthly revenue forecast."""
        return self._repo.get_forecast("revenue", granularity)

    @cached(ttl=600, prefix=_FORECAST_PREFIX)
    def get_product_forecast(self, product_key: int) -> ForecastResult | None:
        """Return the latest stored product demand forecast."""
        return self._repo.get_forecast("product", "monthly", entity_key=product_key)

    @cached(ttl=600, prefix=_FORECAST_PREFIX)
    def get_forecast_summary(self) -> ForecastSummary:
        """Return the summary overview for the forecasting dashboard card."""
        data = self._repo.get_forecast_summary_data()

        next_30d = data.get("next_30d_revenue", Decimal("0"))
        next_3m = data.get("next_3m_revenue", Decimal("0"))

        # Determine trend direction from 30-day forecast vs recent actual
        trend = "stable"
        if next_30d > 0:
            daily_series = self._repo.get_daily_revenue_series(lookback_days=30)
            if daily_series:
                recent_30d = sum(v for _, v in daily_series)
                forecast_30d = float(next_30d)
                if forecast_30d > recent_30d * 1.05:
                    trend = "up"
                elif forecast_30d < recent_30d * 0.95:
                    trend = "down"

        return ForecastSummary(
            last_run_at=data.get("last_run_at"),
            next_30d_revenue=next_30d,
            next_3m_revenue=next_3m,
            revenue_trend=trend,
            mape=data.get("mape"),
            top_growing_products=[
                ProductForecastSummary(
                    product_key=p["product_key"],
                    drug_name=p["drug_name"],
                    forecast_change_pct=p["change_pct"],
                )
                for p in data.get("growing", [])
            ],
            top_declining_products=[
                ProductForecastSummary(
                    product_key=p["product_key"],
                    drug_name=p["drug_name"],
                    forecast_change_pct=p["change_pct"],
                )
                for p in data.get("declining", [])
            ],
        )

    @cached(ttl=120, prefix=_FORECAST_PREFIX)
    def get_customer_segments(
        self, segment: str | None = None, limit: int = 50
    ) -> list[CustomerSegment]:
        """Return customer RFM segments from the feature store."""
        return self._repo.get_customer_segments(segment=segment, limit=limit)

    # ------------------------------------------------------------------
    # Forecast generation (pipeline stage entry point)
    # ------------------------------------------------------------------

    def run_all_forecasts(self) -> dict[str, Any]:
        """Execute all forecasting jobs. Called by the pipeline executor.

        1. Daily revenue forecast (next 30 days, weekly seasonality)
        2. Monthly revenue forecast (next 3 months, yearly seasonality)
        3. Product demand forecast (top 50 products, next 3 months each)
        4. Backtest each for accuracy metrics
        5. Save results to database
        """
        run_at = datetime.now(UTC)
        results: list[ForecastResult] = []
        stats: dict[str, Any] = {}

        # --- 1. Daily revenue ---
        daily_series = self._repo.get_daily_revenue_series(lookback_days=730)
        if daily_series:
            daily_values = [v for _, v in daily_series]
            last_date = daily_series[-1][0]
            start = last_date + timedelta(days=1)
            method_name = select_method(len(daily_values), 7)

            daily_points = _run_method(
                method_name,
                daily_values,
                horizon=30,
                seasonal_periods=7,
                start_date=start,
                monthly=False,
            )
            daily_accuracy = backtest(
                daily_values,
                horizon=min(30, len(daily_values) // 4),
                seasonal_periods=7,
                method=method_name,
            )
            daily_result = ForecastResult(
                entity_type="revenue",
                method=method_name,
                horizon=30,
                granularity="daily",
                points=daily_points,
                accuracy_metrics=daily_accuracy,
            )
            results.append(daily_result)
            stats["daily_revenue"] = {
                "method": method_name,
                "points": len(daily_points),
                "mape": float(daily_accuracy.mape),
            }
            log.info(
                "forecast_daily_revenue_done",
                method=method_name,
                mape=float(daily_accuracy.mape),
            )

        # --- 2. Monthly revenue ---
        monthly_series = self._repo.get_monthly_revenue_series()
        if monthly_series:
            monthly_values = [v for _, v in monthly_series]
            last_period = monthly_series[-1][0]
            # Parse "YYYY-MM" to get start of next month
            year, month = int(last_period[:4]), int(last_period[5:7])
            next_month = month + 1
            next_year = year + (next_month - 1) // 12
            next_month = (next_month - 1) % 12 + 1
            start = date(next_year, next_month, 1)

            method_name = select_method(len(monthly_values), 12)
            monthly_points = _run_method(
                method_name,
                monthly_values,
                horizon=3,
                seasonal_periods=12,
                start_date=start,
                monthly=True,
            )
            monthly_accuracy = backtest(
                monthly_values,
                horizon=min(3, len(monthly_values) // 4),
                seasonal_periods=12,
                method=method_name,
                monthly=True,
            )
            monthly_result = ForecastResult(
                entity_type="revenue",
                method=method_name,
                horizon=3,
                granularity="monthly",
                points=monthly_points,
                accuracy_metrics=monthly_accuracy,
            )
            results.append(monthly_result)
            stats["monthly_revenue"] = {
                "method": method_name,
                "points": len(monthly_points),
                "mape": float(monthly_accuracy.mape),
            }
            log.info("forecast_monthly_revenue_done", method=method_name)

        # --- 3. Product demand (top 50) ---
        top_products = self._repo.get_top_products_by_revenue(limit=50)
        products_forecasted = 0
        for product_key, _drug_name in top_products:
            product_series = self._repo.get_product_monthly_series(product_key)
            if len(product_series) < 3:
                continue
            product_values = [v for _, v in product_series]
            last_period = product_series[-1][0]
            year, month = int(last_period[:4]), int(last_period[5:7])
            next_month = month + 1
            next_year = year + (next_month - 1) // 12
            next_month = (next_month - 1) % 12 + 1
            start = date(next_year, next_month, 1)

            method_name = select_method(len(product_values), 12)
            product_points = _run_method(
                method_name,
                product_values,
                horizon=3,
                seasonal_periods=12,
                start_date=start,
                monthly=True,
            )
            product_accuracy = backtest(
                product_values,
                horizon=min(3, len(product_values) // 4),
                seasonal_periods=12,
                method=method_name,
                monthly=True,
            )
            product_result = ForecastResult(
                entity_type="product",
                entity_key=product_key,
                method=method_name,
                horizon=3,
                granularity="monthly",
                points=product_points,
                accuracy_metrics=product_accuracy,
            )
            results.append(product_result)
            products_forecasted += 1

        stats["products_forecasted"] = products_forecasted
        log.info("forecast_products_done", count=products_forecasted)

        # --- 4. Save all results ---
        rows_written = self._repo.save_forecasts(results, run_at)
        stats["rows_written"] = rows_written
        stats["run_at"] = run_at.isoformat()

        log.info("forecast_run_complete", **stats)
        return stats


# -- helpers ------------------------------------------------------------------


def _run_method(
    method_name: str,
    series: list[float],
    horizon: int,
    seasonal_periods: int,
    start_date: date,
    monthly: bool,
) -> list:
    """Dispatch to the correct forecasting function.

    sma_forecast does not accept seasonal_periods, so we must route explicitly.
    """
    if method_name == "holt_winters":
        return holt_winters_forecast(
            series,
            horizon,
            seasonal_periods,
            start_date=start_date,
            monthly=monthly,
        )
    if method_name == "seasonal_naive":
        return seasonal_naive_forecast(
            series,
            horizon,
            seasonal_periods,
            start_date=start_date,
            monthly=monthly,
        )
    return sma_forecast(
        series,
        horizon,
        start_date=start_date,
        monthly=monthly,
    )
