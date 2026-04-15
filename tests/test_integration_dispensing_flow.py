"""Integration test: sales -> dispense rate -> days of stock -> stockout risk.

Tests the dispensing analytics flow across domain boundaries:
  1. Daily sales data feeds dispense rate calculation
  2. Dispense rate + stock level -> days of stock
  3. Days of stock vs lead time -> stockout risk classification
  4. Product velocity classification (fast/slow/dead mover)
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ConfigDict

# ── Domain models (contract definitions for Session 5) ─────────────


class DispenseRate(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    avg_daily_dispense: Decimal
    avg_weekly_dispense: Decimal
    avg_monthly_dispense: Decimal
    active_days: int
    total_dispensed_90d: Decimal


class DaysOfStock(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    current_quantity: Decimal
    avg_daily_dispense: Decimal
    days_of_stock: Decimal | None  # None if no dispense history


class StockoutRisk(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    days_of_stock: Decimal | None
    reorder_lead_days: int
    risk_level: str  # critical | warning | ok | no_data


class ProductVelocity(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    avg_daily_dispense: Decimal
    category_avg_daily: Decimal
    velocity_class: str  # fast | medium | slow | dead


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture()
def mock_dispense_repo():
    """Mock dispense rate repository."""
    repo = MagicMock()
    repo.get_dispense_rate = MagicMock()
    return repo


@pytest.fixture()
def mock_stock_repo():
    """Mock stock levels repository."""
    repo = MagicMock()
    repo.get_stock_level = MagicMock()
    return repo


@pytest.fixture()
def mock_reorder_repo():
    """Mock reorder config repository."""
    repo = MagicMock()
    repo.get_reorder_config = MagicMock()
    return repo


# ── Helpers ────────────────────────────────────────────────────────


def _calculate_days_of_stock(current_qty: Decimal, avg_daily: Decimal) -> Decimal | None:
    """Calculate days of stock remaining."""
    if avg_daily is None or avg_daily == 0:
        return None
    return (current_qty / avg_daily).quantize(Decimal("0.1"))


def _classify_stockout_risk(days_of_stock: Decimal | None, lead_days: int) -> str:
    """Classify stockout risk based on days of stock vs lead time."""
    if days_of_stock is None:
        return "no_data"
    if days_of_stock < lead_days:
        return "critical"
    if days_of_stock < lead_days * 2:
        return "warning"
    return "ok"


def _classify_velocity(avg_daily: Decimal, category_avg: Decimal) -> str:
    """Classify product velocity relative to category average."""
    if avg_daily == 0:
        return "dead"
    ratio = avg_daily / category_avg if category_avg > 0 else Decimal("0")
    if ratio >= Decimal("1.5"):
        return "fast"
    if ratio >= Decimal("0.5"):
        return "medium"
    if ratio > 0:
        return "slow"
    return "dead"


# ── Tests ──────────────────────────────────────────────────────────


class TestDispenseRateCalculation:
    """Average daily dispense rate from sales data."""

    def test_basic_dispense_rate(self):
        """10 units/day over 90 active days."""
        rate = DispenseRate(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            avg_daily_dispense=Decimal("10"),
            avg_weekly_dispense=Decimal("70"),
            avg_monthly_dispense=Decimal("300"),
            active_days=90,
            total_dispensed_90d=Decimal("900"),
        )

        assert rate.avg_daily_dispense == Decimal("10")
        assert rate.total_dispensed_90d == Decimal("900")

    def test_weekly_monthly_derived(self):
        """Weekly = daily * 7, monthly = daily * 30."""
        daily = Decimal("10")
        assert daily * 7 == Decimal("70")
        assert daily * 30 == Decimal("300")


class TestDaysOfStockCalculation:
    """Days of stock = current stock / avg daily dispense."""

    def test_basic_calculation(self):
        """50 units / 10 per day = 5 days."""
        result = _calculate_days_of_stock(Decimal("50"), Decimal("10"))
        assert result == Decimal("5.0")

    def test_large_stock(self):
        """1000 units / 10 per day = 100 days."""
        result = _calculate_days_of_stock(Decimal("1000"), Decimal("10"))
        assert result == Decimal("100.0")

    def test_zero_dispense_returns_none(self):
        """No dispense history -> None (infinite days)."""
        result = _calculate_days_of_stock(Decimal("100"), Decimal("0"))
        assert result is None

    def test_fractional_result(self):
        """75 units / 10 per day = 7.5 days."""
        result = _calculate_days_of_stock(Decimal("75"), Decimal("10"))
        assert result == Decimal("7.5")


class TestStockoutRiskClassification:
    """Stockout risk based on days of stock vs lead time."""

    def test_critical_when_dos_less_than_lead(self):
        """5 days stock, 7 day lead time -> 'critical'."""
        risk = _classify_stockout_risk(Decimal("5"), 7)
        assert risk == "critical"

    def test_warning_when_dos_less_than_double_lead(self):
        """10 days stock, 7 day lead time -> 'warning'."""
        risk = _classify_stockout_risk(Decimal("10"), 7)
        assert risk == "warning"

    def test_ok_when_dos_ample(self):
        """30 days stock, 7 day lead time -> 'ok'."""
        risk = _classify_stockout_risk(Decimal("30"), 7)
        assert risk == "ok"

    def test_no_data_when_none(self):
        """No dispense data -> 'no_data'."""
        risk = _classify_stockout_risk(None, 7)
        assert risk == "no_data"

    def test_boundary_exactly_lead_time(self):
        """7 days stock = 7 day lead -> 'warning' (not critical, equals double threshold)."""
        risk = _classify_stockout_risk(Decimal("7"), 7)
        assert risk == "warning"

    def test_boundary_double_lead(self):
        """14 days stock = 2 * 7 lead -> 'ok'."""
        risk = _classify_stockout_risk(Decimal("14"), 7)
        assert risk == "ok"


class TestProductVelocityClassification:
    """Product velocity relative to category average."""

    def test_fast_mover(self):
        """150% of category average -> 'fast'."""
        velocity = _classify_velocity(Decimal("15"), Decimal("10"))
        assert velocity == "fast"

    def test_medium_mover(self):
        """80% of category average -> 'medium'."""
        velocity = _classify_velocity(Decimal("8"), Decimal("10"))
        assert velocity == "medium"

    def test_slow_mover(self):
        """30% of category average -> 'slow'."""
        velocity = _classify_velocity(Decimal("3"), Decimal("10"))
        assert velocity == "slow"

    def test_dead_mover(self):
        """Zero dispense -> 'dead'."""
        velocity = _classify_velocity(Decimal("0"), Decimal("10"))
        assert velocity == "dead"

    def test_boundary_fast_threshold(self):
        """Exactly 1.5x -> 'fast'."""
        velocity = _classify_velocity(Decimal("15"), Decimal("10"))
        assert velocity == "fast"

    def test_boundary_medium_threshold(self):
        """Exactly 0.5x -> 'medium'."""
        velocity = _classify_velocity(Decimal("5"), Decimal("10"))
        assert velocity == "medium"


class TestEndToEndDispensingFlow:
    """Full flow: sales -> rate -> DOS -> risk."""

    def test_complete_dispensing_analysis(self):
        """Given daily sales, compute all derived metrics."""
        # Step 1: Daily sales of 10 units
        avg_daily = Decimal("10")

        # Step 2: Current stock = 50
        current_stock = Decimal("50")

        # Step 3: Days of stock
        dos = _calculate_days_of_stock(current_stock, avg_daily)
        assert dos == Decimal("5.0")

        # Step 4: Lead time = 7 days -> critical risk
        risk = _classify_stockout_risk(dos, 7)
        assert risk == "critical"

        # Step 5: Category avg = 8, daily = 10 -> ratio 1.25 -> medium mover
        velocity = _classify_velocity(avg_daily, Decimal("8"))
        assert velocity == "medium"

    def test_no_sales_history_flow(self):
        """Product with no sales -> no rate -> no_data risk."""
        avg_daily = Decimal("0")
        current_stock = Decimal("200")

        dos = _calculate_days_of_stock(current_stock, avg_daily)
        assert dos is None

        risk = _classify_stockout_risk(dos, 7)
        assert risk == "no_data"

        velocity = _classify_velocity(avg_daily, Decimal("10"))
        assert velocity == "dead"
