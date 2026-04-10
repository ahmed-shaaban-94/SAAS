"""Tests for forecasting API endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.forecasting.models import (
    CustomerSegment,
    ForecastPoint,
    ForecastResult,
)
from datapulse.forecasting.repository import ForecastingRepository
from datapulse.forecasting.service import ForecastingService


@pytest.fixture()
def forecast_api_client():
    """FastAPI TestClient with mocked forecasting dependencies."""
    from datapulse.api import deps
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }

    mock_session = MagicMock()
    mock_repo = create_autospec(ForecastingRepository, instance=True)
    mock_svc = ForecastingService(mock_repo)

    app = create_app()
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[deps.get_forecasting_service] = lambda: mock_svc
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    yield client, mock_repo

    app.dependency_overrides.clear()


class TestRevenueEndpoint:
    def test_get_daily_revenue_forecast(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_forecast.return_value = ForecastResult(
            entity_type="revenue",
            method="holt_winters",
            horizon=30,
            granularity="daily",
            points=[
                ForecastPoint(
                    period="2026-04-01",
                    value=Decimal("15000"),
                    lower_bound=Decimal("13000"),
                    upper_bound=Decimal("17000"),
                )
            ],
        )
        resp = client.get("/api/v1/forecasting/revenue?granularity=daily")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_type"] == "revenue"
        assert data["granularity"] == "daily"
        assert len(data["points"]) == 1

    def test_returns_404_when_no_forecast(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_forecast.return_value = None
        resp = client.get("/api/v1/forecasting/revenue")
        assert resp.status_code == 404

    def test_invalid_granularity(self, forecast_api_client):
        client, _ = forecast_api_client
        resp = client.get("/api/v1/forecasting/revenue?granularity=weekly")
        assert resp.status_code == 422


class TestProductEndpoint:
    def test_get_product_forecast(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_forecast.return_value = ForecastResult(
            entity_type="product",
            entity_key=42,
            method="sma",
            horizon=3,
            granularity="monthly",
            points=[],
        )
        resp = client.get("/api/v1/forecasting/products/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_key"] == 42

    def test_returns_404_for_unknown_product(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_forecast.return_value = None
        resp = client.get("/api/v1/forecasting/products/99999")
        assert resp.status_code == 404


class TestSummaryEndpoint:
    def test_get_summary(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_forecast_summary_data.return_value = {
            "last_run_at": datetime(2026, 4, 1, 12, 0),
            "next_30d_revenue": Decimal("500000"),
            "next_3m_revenue": Decimal("1500000"),
            "mape": Decimal("4.5"),
            "growing": [],
            "declining": [],
        }
        mock_repo.get_daily_revenue_series.return_value = []
        resp = client.get("/api/v1/forecasting/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "next_30d_revenue" in data
        assert "revenue_trend" in data


class TestCustomerSegmentsEndpoint:
    def test_get_segments(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_customer_segments.return_value = [
            CustomerSegment(
                customer_key=1,
                customer_id="C001",
                customer_name="Pharmacy X",
                rfm_segment="Champion",
                r_score=5,
                f_score=5,
                m_score=5,
                days_since_last=3,
                frequency=120,
                monetary=Decimal("50000"),
                avg_basket_size=Decimal("416.67"),
                return_rate=Decimal("0.02"),
            )
        ]
        resp = client.get("/api/v1/forecasting/customers/segments")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rfm_segment"] == "Champion"

    def test_filter_by_segment(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_customer_segments.return_value = []
        resp = client.get("/api/v1/forecasting/customers/segments?segment=At%20Risk&limit=10")
        assert resp.status_code == 200


class TestCacheHeaders:
    def test_revenue_has_cache_header(self, forecast_api_client):
        client, mock_repo = forecast_api_client
        mock_repo.get_forecast.return_value = ForecastResult(
            entity_type="revenue",
            method="sma",
            horizon=1,
            granularity="daily",
            points=[
                ForecastPoint(
                    period="2026-04-01",
                    value=Decimal("100"),
                    lower_bound=Decimal("90"),
                    upper_bound=Decimal("110"),
                )
            ],
        )
        resp = client.get("/api/v1/forecasting/revenue")
        assert "max-age=600" in resp.headers.get("Cache-Control", "")
        assert "private" in resp.headers.get("Cache-Control", "")
