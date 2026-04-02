"""Forecasting module — revenue and product demand prediction.

Reads features from the dbt feature store, applies statistical forecasting
(Holt-Winters, SMA, Seasonal Naive), and stores results in PostgreSQL.
"""

from datapulse.forecasting.service import ForecastingService

__all__ = ["ForecastingService"]
