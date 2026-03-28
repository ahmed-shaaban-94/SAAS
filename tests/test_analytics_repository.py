"""Tests for analytics repository."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.repository import AnalyticsRepository


# ------------------------------------------------------------------
# _build_where
# ------------------------------------------------------------------


def test_build_where_no_filters():
    clause, params = AnalyticsRepository._build_where(AnalyticsFilter())
    assert clause == "1=1"
    assert params == {}


def test_build_where_date_range_year_month():
    f = AnalyticsFilter(
        date_range=DateRange(
            start_date=date(2024, 3, 1), end_date=date(2024, 6, 30)
        )
    )
    clause, params = AnalyticsRepository._build_where(f, use_year_month=True)
    assert "start_ym" in params
    assert "end_ym" in params
    assert params["start_ym"] == 202403
    assert params["end_ym"] == 202406
    assert "year * 100 + month BETWEEN :start_ym AND :end_ym" in clause


def test_build_where_date_range_date_key():
    f = AnalyticsFilter(
        date_range=DateRange(
            start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)
        )
    )
    clause, params = AnalyticsRepository._build_where(
        f, use_year_month=False
    )
    assert "date_key BETWEEN :start_date AND :end_date" in clause
    assert params["start_date"] == 20240101
    assert params["end_date"] == 20241231


def test_build_where_multiple_filters():
    f = AnalyticsFilter(site_key=5, category="Analgesic", brand="BrandX")
    clause, params = AnalyticsRepository._build_where(f)
    assert "site_key = :site_key" in clause
    assert "drug_category = :category" in clause
    assert "drug_brand = :brand" in clause
    assert params["site_key"] == 5
    assert params["category"] == "Analgesic"
    assert params["brand"] == "BrandX"


# ------------------------------------------------------------------
# _safe_growth
# ------------------------------------------------------------------


def test_safe_growth_normal():
    result = AnalyticsRepository._safe_growth(Decimal("150"), Decimal("100"))
    assert result == Decimal("50.00")


def test_safe_growth_zero_previous():
    result = AnalyticsRepository._safe_growth(Decimal("100"), Decimal("0"))
    assert result is None


# ------------------------------------------------------------------
# _build_trend
# ------------------------------------------------------------------


def test_build_trend_empty():
    trend = AnalyticsRepository._build_trend([])
    assert trend.points == []
    assert trend.total == Decimal("0")
    assert trend.average == Decimal("0")
    assert trend.minimum == Decimal("0")
    assert trend.maximum == Decimal("0")
    assert trend.growth_pct is None


def test_build_trend_single_point():
    rows = [("2024-01", 100)]
    trend = AnalyticsRepository._build_trend(rows)
    assert len(trend.points) == 1
    assert trend.total == Decimal("100")
    assert trend.average == Decimal("100.00")
    assert trend.growth_pct is None  # needs >= 2 points


def test_build_trend_multiple():
    rows = [("2024-01", 100), ("2024-02", 200), ("2024-03", 150)]
    trend = AnalyticsRepository._build_trend(rows)
    assert len(trend.points) == 3
    assert trend.total == Decimal("450")
    assert trend.average == Decimal("150.00")
    assert trend.minimum == Decimal("100")
    assert trend.maximum == Decimal("200")
    # growth = (150 - 100) / 100 * 100 = 50.00
    assert trend.growth_pct == Decimal("50.00")


# ------------------------------------------------------------------
# _build_ranking
# ------------------------------------------------------------------


def test_build_ranking_empty(analytics_repo):
    result = analytics_repo._build_ranking([])
    assert result.items == []
    assert result.total == Decimal("0")


def test_build_ranking_items(analytics_repo):
    rows = [(1, "Product A", 500), (2, "Product B", 300), (3, "Product C", 200)]
    result = analytics_repo._build_ranking(rows)
    assert len(result.items) == 3
    assert result.total == Decimal("1000")
    assert result.items[0].rank == 1
    assert result.items[0].name == "Product A"
    assert result.items[0].pct_of_total == Decimal("50.00")
    assert result.items[1].rank == 2
    assert result.items[2].pct_of_total == Decimal("20.00")


# ------------------------------------------------------------------
# get_kpi_summary
# ------------------------------------------------------------------


def test_get_kpi_summary_no_data(analytics_repo, mock_session):
    mock_session.execute.return_value.fetchone.return_value = None
    result = analytics_repo.get_kpi_summary(date(2025, 1, 15))
    assert result.today_net == Decimal("0")
    assert result.mtd_net == Decimal("0")
    assert result.ytd_net == Decimal("0")
    assert result.daily_transactions == 0
    assert result.daily_customers == 0


def test_get_kpi_summary_with_data(analytics_repo, mock_session):
    # First call: daily row; second call: prev month; third call: prev year
    daily_row = (1000, 25000, 300000, 42, 15)
    prev_month_row = (20000,)
    prev_year_row = (250000,)

    mock_session.execute.return_value.fetchone.side_effect = [
        daily_row,
        prev_month_row,
        prev_year_row,
    ]

    result = analytics_repo.get_kpi_summary(date(2025, 6, 15))
    assert result.today_net == Decimal("1000")
    assert result.mtd_net == Decimal("25000")
    assert result.ytd_net == Decimal("300000")
    assert result.daily_transactions == 42
    assert result.daily_customers == 15
    # MoM: (25000 - 20000) / 20000 * 100 = 25.00
    assert result.mom_growth_pct == Decimal("25.00")
    # YoY: (300000 - 250000) / 250000 * 100 = 20.00
    assert result.yoy_growth_pct == Decimal("20.00")


# ------------------------------------------------------------------
# get_daily_trend
# ------------------------------------------------------------------


def test_get_daily_trend(analytics_repo, mock_session):
    mock_session.execute.return_value.fetchall.return_value = [
        ("2025-01-01", 500),
        ("2025-01-02", 700),
    ]
    result = analytics_repo.get_daily_trend(AnalyticsFilter())
    assert len(result.points) == 2
    assert result.total == Decimal("1200")
    assert result.points[0].period == "2025-01-01"
    assert result.points[1].value == Decimal("700")
    # growth = (700 - 500) / 500 * 100 = 40.00
    assert result.growth_pct == Decimal("40.00")


# ------------------------------------------------------------------
# get_top_products
# ------------------------------------------------------------------


def test_get_top_products(analytics_repo, mock_session):
    mock_session.execute.return_value.fetchall.return_value = [
        (1, "Drug A", 5000),
        (2, "Drug B", 3000),
        (3, "Drug C", 2000),
    ]
    result = analytics_repo.get_top_products(AnalyticsFilter())
    assert len(result.items) == 3
    assert result.total == Decimal("10000")
    assert result.items[0].name == "Drug A"
    assert result.items[0].rank == 1
    assert result.items[0].pct_of_total == Decimal("50.00")


# ------------------------------------------------------------------
# get_return_analysis
# ------------------------------------------------------------------


def test_get_return_analysis_empty(analytics_repo, mock_session):
    mock_session.execute.return_value.fetchall.return_value = []
    result = analytics_repo.get_return_analysis(AnalyticsFilter())
    assert result == []
