"""Tests for monthly_trend field on detail models (ProductPerformance, CustomerAnalytics, StaffPerformance).

Pure unit tests -- no database required. Validates that the monthly_trend
field (list[TimeSeriesPoint]) is accepted, defaults to an empty list, and
serializes correctly.
"""

from decimal import Decimal

from datapulse.analytics.models import (
    CustomerAnalytics,
    ProductPerformance,
    StaffPerformance,
    TimeSeriesPoint,
)


# --- Helpers ---


def _make_product(**overrides) -> ProductPerformance:
    defaults = dict(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="BrandX",
        drug_category="Analgesic",
        total_quantity=Decimal("1000"),
        total_sales=Decimal("5000.00"),
        total_net_amount=Decimal("4500.00"),
        return_rate=Decimal("2.50"),
        unique_customers=30,
    )
    defaults.update(overrides)
    return ProductPerformance(**defaults)


def _make_customer(**overrides) -> CustomerAnalytics:
    defaults = dict(
        customer_key=1,
        customer_id="C001",
        customer_name="Pharmacy ABC",
        total_quantity=Decimal("500"),
        total_net_amount=Decimal("10000.00"),
        transaction_count=25,
        unique_products=12,
        return_count=2,
    )
    defaults.update(overrides)
    return CustomerAnalytics(**defaults)


def _make_staff(**overrides) -> StaffPerformance:
    defaults = dict(
        staff_key=1,
        staff_id="S001",
        staff_name="Ahmed",
        staff_position="Sales Rep",
        total_net_amount=Decimal("50000.00"),
        transaction_count=150,
        avg_transaction_value=Decimal("333.33"),
        unique_customers=40,
    )
    defaults.update(overrides)
    return StaffPerformance(**defaults)


def _sample_trend() -> list[TimeSeriesPoint]:
    return [
        TimeSeriesPoint(period="2024-01", value=Decimal("1200.50")),
        TimeSeriesPoint(period="2024-02", value=Decimal("1350.75")),
        TimeSeriesPoint(period="2024-03", value=Decimal("980.00")),
    ]


# --- TimeSeriesPoint serialization ---


def test_time_series_point_serialization():
    """TimeSeriesPoint should serialize period and value correctly."""
    point = TimeSeriesPoint(period="2024-06", value=Decimal("42.10"))
    data = point.model_dump()
    assert data["period"] == "2024-06"
    # JsonDecimal serializes Decimal -> float for JSON output
    assert data["value"] == 42.10


def test_time_series_point_json_round_trip():
    """TimeSeriesPoint should survive a JSON round-trip."""
    point = TimeSeriesPoint(period="2025-01", value=Decimal("9999.99"))
    json_str = point.model_dump_json()
    restored = TimeSeriesPoint.model_validate_json(json_str)
    assert restored.period == "2025-01"
    assert restored.value == Decimal("9999.99")


# --- ProductPerformance monthly_trend ---


def test_product_performance_monthly_trend_default():
    """monthly_trend should default to an empty list when not provided."""
    product = _make_product()
    assert product.monthly_trend == []


def test_product_performance_monthly_trend_accepts_points():
    """ProductPerformance should accept a list of TimeSeriesPoint."""
    trend = _sample_trend()
    product = _make_product(monthly_trend=trend)
    assert len(product.monthly_trend) == 3
    assert product.monthly_trend[0].period == "2024-01"
    assert product.monthly_trend[0].value == Decimal("1200.50")
    assert product.monthly_trend[2].period == "2024-03"


def test_product_performance_monthly_trend_serializes():
    """monthly_trend should appear in model_dump output."""
    trend = _sample_trend()
    product = _make_product(monthly_trend=trend)
    data = product.model_dump()
    assert "monthly_trend" in data
    assert len(data["monthly_trend"]) == 3
    assert data["monthly_trend"][1]["period"] == "2024-02"


# --- CustomerAnalytics monthly_trend ---


def test_customer_analytics_monthly_trend_default():
    """monthly_trend should default to an empty list when not provided."""
    customer = _make_customer()
    assert customer.monthly_trend == []


def test_customer_analytics_monthly_trend_accepts_points():
    """CustomerAnalytics should accept a list of TimeSeriesPoint."""
    trend = _sample_trend()
    customer = _make_customer(monthly_trend=trend)
    assert len(customer.monthly_trend) == 3
    assert customer.monthly_trend[1].period == "2024-02"
    assert customer.monthly_trend[1].value == Decimal("1350.75")


def test_customer_analytics_monthly_trend_serializes():
    """monthly_trend should appear in model_dump output."""
    trend = _sample_trend()
    customer = _make_customer(monthly_trend=trend)
    data = customer.model_dump()
    assert "monthly_trend" in data
    assert len(data["monthly_trend"]) == 3
    assert data["monthly_trend"][0]["period"] == "2024-01"


# --- StaffPerformance monthly_trend ---


def test_staff_performance_monthly_trend_default():
    """monthly_trend should default to an empty list when not provided."""
    staff = _make_staff()
    assert staff.monthly_trend == []


def test_staff_performance_monthly_trend_accepts_points():
    """StaffPerformance should accept a list of TimeSeriesPoint."""
    trend = _sample_trend()
    staff = _make_staff(monthly_trend=trend)
    assert len(staff.monthly_trend) == 3
    assert staff.monthly_trend[2].period == "2024-03"
    assert staff.monthly_trend[2].value == Decimal("980.00")


def test_staff_performance_monthly_trend_serializes():
    """monthly_trend should appear in model_dump output."""
    trend = _sample_trend()
    staff = _make_staff(monthly_trend=trend)
    data = staff.model_dump()
    assert "monthly_trend" in data
    assert len(data["monthly_trend"]) == 3
    assert data["monthly_trend"][2]["period"] == "2024-03"


# --- Edge cases ---


def test_monthly_trend_single_point():
    """Models should accept a trend with exactly one point."""
    trend = [TimeSeriesPoint(period="2024-12", value=Decimal("500.00"))]
    product = _make_product(monthly_trend=trend)
    customer = _make_customer(monthly_trend=trend)
    staff = _make_staff(monthly_trend=trend)

    assert len(product.monthly_trend) == 1
    assert len(customer.monthly_trend) == 1
    assert len(staff.monthly_trend) == 1


def test_monthly_trend_zero_values():
    """TimeSeriesPoint should accept zero values."""
    trend = [TimeSeriesPoint(period="2024-01", value=Decimal("0"))]
    product = _make_product(monthly_trend=trend)
    assert product.monthly_trend[0].value == Decimal("0")


def test_monthly_trend_negative_values():
    """TimeSeriesPoint should accept negative values (e.g. returns/credits)."""
    trend = [TimeSeriesPoint(period="2024-01", value=Decimal("-250.00"))]
    product = _make_product(monthly_trend=trend)
    assert product.monthly_trend[0].value == Decimal("-250.00")
