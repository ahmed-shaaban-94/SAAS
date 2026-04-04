"""Tests for Enhancement 3 — Analytics Dashboard Upgrades.

Covers: billing breakdown, customer type breakdown, top movers,
site detail, product hierarchy, and KPISummary expansion.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.comparison_repository import ComparisonRepository
from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.hierarchy_repository import HierarchyRepository
from datapulse.analytics.models import (
    AnalyticsFilter,
    BillingBreakdown,
    CustomerTypeBreakdown,
    DateRange,
    KPISummary,
    ProductHierarchy,
    SiteDetail,
    TopMovers,
)

# ------------------------------------------------------------------
# KPISummary model defaults (backward compatibility)
# ------------------------------------------------------------------


def test_kpi_summary_backward_compat():
    """Old responses without new fields should parse with defaults."""
    kpi = KPISummary(
        today_gross=100,
        mtd_gross=1000,
        ytd_gross=10000,
        daily_transactions=5,
        daily_customers=3,
    )
    assert kpi.avg_basket_size == 0
    assert kpi.daily_returns == 0
    assert kpi.mtd_transactions == 0
    assert kpi.ytd_transactions == 0
    assert kpi.sparkline == []


def test_kpi_summary_with_new_fields():
    """KPISummary correctly stores new Enhancement 3 fields."""
    kpi = KPISummary(
        today_gross=100,
        mtd_gross=1000,
        ytd_gross=10000,
        daily_transactions=5,
        daily_customers=3,
        avg_basket_size=Decimal("50.25"),
        daily_returns=2,
        mtd_transactions=150,
        ytd_transactions=1800,
    )
    assert kpi.avg_basket_size == Decimal("50.25")
    assert kpi.daily_returns == 2


# ------------------------------------------------------------------
# BreakdownRepository
# ------------------------------------------------------------------


@pytest.fixture()
def breakdown_repo():
    session = MagicMock()
    return BreakdownRepository(session), session


def test_billing_breakdown_empty(breakdown_repo):
    repo, session = breakdown_repo
    session.execute.return_value.fetchall.return_value = []
    result = repo.get_billing_breakdown(AnalyticsFilter())
    assert isinstance(result, BillingBreakdown)
    assert result.items == []
    assert result.total_transactions == 0
    assert result.total_sales == Decimal("0")


def test_billing_breakdown_pct_of_total(breakdown_repo):
    repo, session = breakdown_repo
    session.execute.return_value.fetchall.return_value = [
        ("Cash", 60, 6000),
        ("Credit", 30, 3000),
        ("Delivery", 10, 1000),
    ]
    result = repo.get_billing_breakdown(AnalyticsFilter())
    assert len(result.items) == 3
    assert result.total_transactions == 100
    assert result.total_sales == Decimal("10000")
    # Verify percentages sum to ~100
    total_pct = sum(item.pct_of_total for item in result.items)
    assert abs(total_pct - Decimal("100")) < Decimal("0.1")


def test_customer_type_other_count(breakdown_repo):
    repo, session = breakdown_repo
    session.execute.return_value.fetchall.return_value = [
        ("2024-01", 30, 20, 100),  # walk_in=30, insurance=20, total=100
    ]
    result = repo.get_customer_type_breakdown(AnalyticsFilter())
    assert isinstance(result, CustomerTypeBreakdown)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.walk_in_count == 30
    assert item.insurance_count == 20
    assert item.other_count == 50  # 100 - 30 - 20
    assert item.total_count == 100


def test_customer_type_breakdown_ordering(breakdown_repo):
    repo, session = breakdown_repo
    session.execute.return_value.fetchall.return_value = [
        ("2024-01", 10, 5, 20),
        ("2024-02", 15, 8, 30),
        ("2024-03", 20, 10, 40),
    ]
    result = repo.get_customer_type_breakdown(AnalyticsFilter())
    assert len(result.items) == 3
    assert result.items[0].period == "2024-01"
    assert result.items[2].period == "2024-03"


# ------------------------------------------------------------------
# ComparisonRepository
# ------------------------------------------------------------------


@pytest.fixture()
def comparison_repo():
    session = MagicMock()
    return ComparisonRepository(session), session


def test_top_movers_both_periods(comparison_repo):
    repo, session = comparison_repo
    # Two execute calls: current period, previous period
    current_rows = [(1, "Drug A", 5000), (2, "Drug B", 3000)]
    previous_rows = [(1, "Drug A", 4000), (2, "Drug B", 3500)]
    session.execute.return_value.fetchall.side_effect = [
        current_rows,
        previous_rows,
    ]

    current_f = AnalyticsFilter(
        date_range=DateRange(start_date=date(2024, 2, 1), end_date=date(2024, 2, 28))
    )
    previous_f = AnalyticsFilter(
        date_range=DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
    )
    result = repo.get_top_movers("product", current_f, previous_f, limit=5)
    assert isinstance(result, TopMovers)
    assert result.entity_type == "product"


def test_top_movers_invalid_entity_type(comparison_repo):
    repo, _ = comparison_repo
    f = AnalyticsFilter()
    with pytest.raises(ValueError, match="Invalid entity_type"):
        repo.get_top_movers("invalid", f, f)


# ------------------------------------------------------------------
# HierarchyRepository
# ------------------------------------------------------------------


@pytest.fixture()
def hierarchy_repo():
    session = MagicMock()
    return HierarchyRepository(session), session


def test_product_hierarchy_empty(hierarchy_repo):
    repo, session = hierarchy_repo
    session.execute.return_value.fetchall.return_value = []
    result = repo.get_product_hierarchy(AnalyticsFilter())
    assert isinstance(result, ProductHierarchy)
    assert result.categories == []


def test_product_hierarchy_nesting(hierarchy_repo):
    repo, session = hierarchy_repo
    session.execute.return_value.fetchall.return_value = [
        ("Analgesic", "BrandA", 1, "Drug1", 5000, 100),
        ("Analgesic", "BrandA", 2, "Drug2", 3000, 80),
        ("Analgesic", "BrandB", 3, "Drug3", 2000, 60),
        ("Antibiotic", "BrandC", 4, "Drug4", 4000, 90),
    ]
    result = repo.get_product_hierarchy(AnalyticsFilter())
    assert len(result.categories) == 2

    # Categories sorted by total desc: Analgesic (10000) > Antibiotic (4000)
    analgesic = result.categories[0]
    assert analgesic.category == "Analgesic"
    assert analgesic.total_sales == Decimal("10000")
    assert len(analgesic.brands) == 2

    # Brands sorted by total desc: BrandA (8000) > BrandB (2000)
    assert analgesic.brands[0].brand == "BrandA"
    assert len(analgesic.brands[0].products) == 2


# ------------------------------------------------------------------
# DetailRepository — get_site_detail
# ------------------------------------------------------------------


@pytest.fixture()
def detail_repo():
    session = MagicMock()
    return DetailRepository(session), session


def test_get_site_detail_not_found(detail_repo):
    repo, session = detail_repo
    session.execute.return_value.fetchone.return_value = None
    result = repo.get_site_detail(999)
    assert result is None


def test_get_site_detail_with_data(detail_repo):
    repo, session = detail_repo
    site_row = (
        1,
        "S01",
        "Main Pharmacy",
        "John Manager",
        Decimal("500000"),
        2000,
        800,
        10,
        Decimal("0.65"),
        Decimal("0.30"),
        Decimal("0.02"),
    )
    trend_rows = [("2024-01", 40000), ("2024-02", 45000)]

    session.execute.return_value.fetchone.return_value = site_row
    session.execute.return_value.fetchall.return_value = trend_rows

    result = repo.get_site_detail(1)
    assert isinstance(result, SiteDetail)
    assert result.site_key == 1
    assert result.site_name == "Main Pharmacy"
    assert result.area_manager == "John Manager"
    assert result.total_sales == Decimal("500000")
    assert result.transaction_count == 2000
    assert result.unique_customers == 800


# ------------------------------------------------------------------
# AnalyticsService — new methods
# ------------------------------------------------------------------


def test_service_get_billing_breakdown(analytics_service, mock_breakdown_repo):
    from datapulse.analytics.models import BillingBreakdown

    mock_breakdown_repo.get_billing_breakdown.return_value = BillingBreakdown(
        items=[],
        total_transactions=0,
        total_sales=Decimal("0"),
    )
    result = analytics_service.get_billing_breakdown()
    assert isinstance(result, BillingBreakdown)
    mock_breakdown_repo.get_billing_breakdown.assert_called_once()


def test_service_get_customer_type_breakdown(analytics_service, mock_breakdown_repo):
    mock_breakdown_repo.get_customer_type_breakdown.return_value = CustomerTypeBreakdown(
        items=[],
    )
    result = analytics_service.get_customer_type_breakdown()
    assert isinstance(result, CustomerTypeBreakdown)
    mock_breakdown_repo.get_customer_type_breakdown.assert_called_once()


def test_service_get_product_hierarchy(analytics_service, mock_hierarchy_repo):
    mock_hierarchy_repo.get_product_hierarchy.return_value = ProductHierarchy(
        categories=[],
    )
    result = analytics_service.get_product_hierarchy()
    assert isinstance(result, ProductHierarchy)
    mock_hierarchy_repo.get_product_hierarchy.assert_called_once()


def test_service_get_site_detail(analytics_service, mock_detail_repo):
    mock_detail_repo.get_site_detail.return_value = None
    result = analytics_service.get_site_detail(999)
    assert result is None
    mock_detail_repo.get_site_detail.assert_called_once_with(999)
