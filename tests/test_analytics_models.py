"""Tests for analytics Pydantic models."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datapulse.analytics.models import (
    AnalyticsFilter,
    CustomerAnalytics,
    DateRange,
    KPISummary,
    ProductPerformance,
    RankingItem,
    RankingResult,
    ReturnAnalysis,
    StaffPerformance,
    TimeSeriesPoint,
    TrendResult,
)


def test_date_range_creation():
    dr = DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    assert dr.start_date == date(2024, 1, 1)
    assert dr.end_date == date(2024, 12, 31)


def test_date_range_frozen():
    dr = DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    with pytest.raises(ValidationError):
        dr.start_date = date(2025, 1, 1)


def test_analytics_filter_defaults():
    f = AnalyticsFilter()
    assert f.limit == 10
    assert f.date_range is None
    assert f.site_key is None
    assert f.category is None
    assert f.brand is None
    assert f.staff_key is None


def test_analytics_filter_limit_bounds():
    with pytest.raises(ValidationError):
        AnalyticsFilter(limit=0)
    with pytest.raises(ValidationError):
        AnalyticsFilter(limit=101)


def test_time_series_point():
    p = TimeSeriesPoint(period="2024-01", value=Decimal("100.50"))
    assert p.period == "2024-01"
    assert p.value == Decimal("100.50")


def test_trend_result_empty():
    t = TrendResult(
        points=[],
        total=Decimal("0"),
        average=Decimal("0"),
        minimum=Decimal("0"),
        maximum=Decimal("0"),
        growth_pct=None,
    )
    assert t.points == []
    assert t.total == Decimal("0")
    assert t.average == Decimal("0")
    assert t.minimum == Decimal("0")
    assert t.maximum == Decimal("0")
    assert t.growth_pct is None


def test_kpi_summary():
    kpi = KPISummary(
        today_net=Decimal("1000.00"),
        mtd_net=Decimal("25000.00"),
        ytd_net=Decimal("300000.00"),
        mom_growth_pct=Decimal("5.25"),
        yoy_growth_pct=Decimal("12.50"),
        daily_transactions=42,
        daily_customers=15,
    )
    assert kpi.today_net == Decimal("1000.00")
    assert kpi.daily_transactions == 42
    assert kpi.daily_customers == 15
    with pytest.raises(ValidationError):
        kpi.today_net = Decimal("0")


def test_ranking_item():
    item = RankingItem(
        rank=1,
        key=10,
        name="Product A",
        value=Decimal("500.00"),
        pct_of_total=Decimal("25.00"),
    )
    assert item.rank == 1
    assert item.name == "Product A"
    assert item.pct_of_total == Decimal("25.00")


def test_ranking_result_empty():
    r = RankingResult(items=[], total=Decimal("0"))
    assert r.items == []
    assert r.total == Decimal("0")


def test_product_performance():
    p = ProductPerformance(
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
    assert p.drug_code == "D001"
    assert p.total_net_amount == Decimal("4500.00")
    assert p.unique_customers == 30


def test_customer_analytics():
    c = CustomerAnalytics(
        customer_key=1,
        customer_id="C001",
        customer_name="Pharmacy ABC",
        total_quantity=Decimal("500"),
        total_net_amount=Decimal("10000.00"),
        transaction_count=25,
        unique_products=12,
        return_count=2,
    )
    assert c.customer_id == "C001"
    assert c.transaction_count == 25
    assert c.return_count == 2


def test_staff_performance():
    s = StaffPerformance(
        staff_key=1,
        staff_id="S001",
        staff_name="Ahmed",
        staff_position="Sales Rep",
        total_net_amount=Decimal("50000.00"),
        transaction_count=150,
        avg_transaction_value=Decimal("333.33"),
        unique_customers=40,
    )
    assert s.staff_id == "S001"
    assert s.staff_position == "Sales Rep"
    assert s.avg_transaction_value == Decimal("333.33")


def test_return_analysis():
    r = ReturnAnalysis(
        drug_name="Amoxicillin",
        customer_name="Pharmacy XYZ",
        return_quantity=Decimal("50"),
        return_amount=Decimal("2500.00"),
        return_count=3,
    )
    assert r.drug_name == "Amoxicillin"
    assert r.return_amount == Decimal("2500.00")
    assert r.return_count == 3


def test_all_models_frozen():
    """All analytics models must be immutable (frozen=True)."""
    instances = [
        DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)),
        AnalyticsFilter(),
        TimeSeriesPoint(period="2024-01", value=Decimal("1")),
        TrendResult(
            points=[], total=Decimal("0"), average=Decimal("0"),
            minimum=Decimal("0"), maximum=Decimal("0"),
        ),
        KPISummary(
            today_net=Decimal("0"), mtd_net=Decimal("0"), ytd_net=Decimal("0"),
            daily_transactions=0, daily_customers=0,
        ),
        RankingItem(
            rank=1, key=1, name="x", value=Decimal("1"),
            pct_of_total=Decimal("100"),
        ),
        RankingResult(items=[], total=Decimal("0")),
        ProductPerformance(
            product_key=1, drug_code="D", drug_name="N", drug_brand="B",
            drug_category="C", total_quantity=Decimal("0"),
            total_sales=Decimal("0"), total_net_amount=Decimal("0"),
            return_rate=Decimal("0"), unique_customers=0,
        ),
        CustomerAnalytics(
            customer_key=1, customer_id="C", customer_name="N",
            total_quantity=Decimal("0"), total_net_amount=Decimal("0"),
            transaction_count=0, unique_products=0, return_count=0,
        ),
        StaffPerformance(
            staff_key=1, staff_id="S", staff_name="N", staff_position="P",
            total_net_amount=Decimal("0"), transaction_count=0,
            avg_transaction_value=Decimal("0"), unique_customers=0,
        ),
        ReturnAnalysis(
            drug_name="D", customer_name="C", return_quantity=Decimal("0"),
            return_amount=Decimal("0"), return_count=0,
        ),
    ]

    for instance in instances:
        # Pick the first field name from the model class (not instance)
        field_name = next(iter(type(instance).model_fields))
        with pytest.raises(ValidationError):
            setattr(instance, field_name, None)
