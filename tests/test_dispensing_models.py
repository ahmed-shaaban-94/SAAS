"""Tests for dispensing analytics Pydantic models — immutability and validation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from datapulse.dispensing.models import (
    DaysOfStock,
    DispenseRate,
    DispensingFilter,
    StockoutRisk,
    VelocityClassification,
)

# ------------------------------------------------------------------
# DispenseRate
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dispense_rate_frozen():
    rate = DispenseRate(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_code="S01",
        site_name="Main",
        active_days=45,
        total_dispensed_90d=Decimal("450"),
        avg_daily_dispense=Decimal("10.0"),
        avg_weekly_dispense=Decimal("70.0"),
        avg_monthly_dispense=Decimal("300.0"),
    )
    with pytest.raises(ValueError):  # Pydantic frozen model raises ValidationError(ValueError)
        rate.drug_code = "CHANGED"  # type: ignore[misc]


@pytest.mark.unit
def test_dispense_rate_nullable_fields():
    rate = DispenseRate(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_code="S01",
        site_name="Main",
        active_days=0,
        total_dispensed_90d=Decimal("0"),
        avg_daily_dispense=None,
        avg_weekly_dispense=None,
        avg_monthly_dispense=None,
    )
    assert rate.avg_daily_dispense is None
    assert rate.last_dispense_date_key is None


# ------------------------------------------------------------------
# DaysOfStock
# ------------------------------------------------------------------


@pytest.mark.unit
def test_days_of_stock_none_when_no_history():
    """days_of_stock should accept None (product with no dispense history)."""
    dos = DaysOfStock(
        product_key=2,
        site_key=1,
        drug_code="D002",
        drug_name="Amoxicillin",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("50"),
        avg_daily_dispense=None,
        days_of_stock=None,
        avg_weekly_dispense=None,
        avg_monthly_dispense=None,
    )
    assert dos.days_of_stock is None


@pytest.mark.unit
def test_days_of_stock_value():
    dos = DaysOfStock(
        product_key=3,
        site_key=1,
        drug_code="D003",
        drug_name="Ibuprofen",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("100"),
        avg_daily_dispense=Decimal("5.0"),
        days_of_stock=Decimal("20.0"),
        avg_weekly_dispense=Decimal("35.0"),
        avg_monthly_dispense=Decimal("150.0"),
    )
    assert dos.days_of_stock == Decimal("20.0")


# ------------------------------------------------------------------
# VelocityClassification
# ------------------------------------------------------------------


@pytest.mark.unit
def test_velocity_classification_fields():
    vc = VelocityClassification(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        drug_category="Analgesics",
        lifecycle_phase="Mature",
        velocity_class="fast_mover",
        avg_daily_dispense=Decimal("10.0"),
        category_avg_daily=Decimal("5.0"),
    )
    assert vc.velocity_class == "fast_mover"
    assert vc.lifecycle_phase == "Mature"


@pytest.mark.unit
def test_velocity_classification_nullable_lifecycle():
    vc = VelocityClassification(
        product_key=2,
        drug_code="D002",
        drug_name="NewDrug",
        drug_brand="Brand",
        drug_category="Antibiotics",
        lifecycle_phase=None,
        velocity_class="dead_stock",
        avg_daily_dispense=Decimal("0"),
        category_avg_daily=None,
    )
    assert vc.lifecycle_phase is None


# ------------------------------------------------------------------
# StockoutRisk
# ------------------------------------------------------------------


@pytest.mark.unit
def test_stockout_risk_fields():
    risk = StockoutRisk(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("0"),
        days_of_stock=None,
        avg_daily_dispense=Decimal("10.0"),
        reorder_point=Decimal("20"),
        reorder_lead_days=7,
        min_stock=Decimal("10"),
        risk_level="stockout",
        suggested_reorder_qty=Decimal("20"),
    )
    assert risk.risk_level == "stockout"
    assert risk.days_of_stock is None


# ------------------------------------------------------------------
# DispensingFilter
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dispensing_filter_defaults():
    f = DispensingFilter()
    assert f.site_key is None
    assert f.drug_code is None
    assert f.limit == 100


@pytest.mark.unit
def test_dispensing_filter_frozen():
    f = DispensingFilter(site_key=1)
    with pytest.raises(ValueError):  # Pydantic frozen model raises ValidationError(ValueError)
        f.site_key = 2  # type: ignore[misc]
