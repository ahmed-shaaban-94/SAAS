"""Tests for forecasting Pydantic models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datapulse.forecasting.models import (
    CustomerSegment,
    ForecastAccuracy,
    ForecastPoint,
    ForecastResult,
    ForecastSummary,
    ProductForecastSummary,
)


class TestForecastPoint:
    def test_creation(self):
        p = ForecastPoint(
            period="2026-04-01",
            value=Decimal("1234.56"),
            lower_bound=Decimal("1100.00"),
            upper_bound=Decimal("1370.00"),
        )
        assert p.period == "2026-04-01"
        assert p.value == Decimal("1234.56")

    def test_frozen(self):
        p = ForecastPoint(
            period="2026-04-01",
            value=Decimal("100"),
            lower_bound=Decimal("90"),
            upper_bound=Decimal("110"),
        )
        with pytest.raises(ValidationError):
            p.value = Decimal("200")  # type: ignore[misc]

    def test_json_roundtrip(self):
        p = ForecastPoint(
            period="2026-04",
            value=Decimal("999.99"),
            lower_bound=Decimal("900.00"),
            upper_bound=Decimal("1100.00"),
        )
        data = p.model_dump(mode="json")
        assert isinstance(data["value"], float)
        assert data["period"] == "2026-04"


class TestForecastAccuracy:
    def test_creation(self):
        a = ForecastAccuracy(
            mape=Decimal("5.23"),
            mae=Decimal("120.50"),
            rmse=Decimal("150.75"),
            coverage=Decimal("82.00"),
        )
        assert a.mape == Decimal("5.23")
        assert a.coverage == Decimal("82.00")


class TestForecastResult:
    def test_revenue_forecast(self):
        r = ForecastResult(
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
        assert r.entity_key is None
        assert r.accuracy_metrics is None

    def test_product_forecast(self):
        r = ForecastResult(
            entity_type="product",
            entity_key=42,
            method="sma",
            horizon=3,
            granularity="monthly",
            points=[],
            accuracy_metrics=ForecastAccuracy(
                mape=Decimal("10"),
                mae=Decimal("50"),
                rmse=Decimal("60"),
                coverage=Decimal("75"),
            ),
        )
        assert r.entity_key == 42
        assert r.accuracy_metrics is not None


class TestForecastSummary:
    def test_defaults(self):
        s = ForecastSummary()
        assert s.last_run_at is None
        assert s.next_30d_revenue == Decimal("0")
        assert s.revenue_trend == "stable"
        assert s.top_growing_products == []

    def test_full(self):
        s = ForecastSummary(
            last_run_at=datetime(2026, 4, 1, 12, 0),
            next_30d_revenue=Decimal("500000"),
            next_3m_revenue=Decimal("1500000"),
            revenue_trend="up",
            mape=Decimal("4.5"),
            top_growing_products=[
                ProductForecastSummary(
                    product_key=1,
                    drug_name="Drug A",
                    forecast_change_pct=Decimal("15.3"),
                )
            ],
        )
        assert s.revenue_trend == "up"
        assert len(s.top_growing_products) == 1


class TestCustomerSegment:
    def test_creation(self):
        cs = CustomerSegment(
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
        assert cs.rfm_segment == "Champion"
        assert cs.r_score == 5
