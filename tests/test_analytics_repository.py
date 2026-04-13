"""Tests for analytics repository and shared query helpers."""

from datetime import date
from decimal import Decimal

from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.queries import (
    build_ranking,
    build_trend,
    build_where,
    safe_growth,
)

# ------------------------------------------------------------------
# build_where (shared helper)
# ------------------------------------------------------------------


def test_build_where_no_filters():
    clause, params = build_where(AnalyticsFilter())
    assert clause == "1=1"
    assert params == {}


def test_build_where_date_range_year_month():
    f = AnalyticsFilter(
        date_range=DateRange(start_date=date(2024, 3, 1), end_date=date(2024, 6, 30))
    )
    clause, params = build_where(f, use_year_month=True)
    assert "start_ym" in params
    assert "end_ym" in params
    assert params["start_ym"] == 202403
    assert params["end_ym"] == 202406
    assert "year * 100 + month BETWEEN :start_ym AND :end_ym" in clause


def test_build_where_date_range_date_key():
    f = AnalyticsFilter(
        date_range=DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    )
    clause, params = build_where(f, use_year_month=False)
    assert "date_key BETWEEN :start_date AND :end_date" in clause
    assert params["start_date"] == 20240101
    assert params["end_date"] == 20241231


def test_build_where_multiple_filters():
    f = AnalyticsFilter(site_key=5, category="Analgesic", brand="BrandX")
    clause, params = build_where(f)
    assert "site_key = :site_key" in clause
    assert "drug_category = :category" in clause
    assert "drug_brand = :brand" in clause
    assert params["site_key"] == 5
    assert params["category"] == "Analgesic"
    assert params["brand"] == "BrandX"


# ------------------------------------------------------------------
# safe_growth (shared helper)
# ------------------------------------------------------------------


def test_safe_growth_normal():
    result = safe_growth(Decimal("150"), Decimal("100"))
    assert result == Decimal("50.00")


def test_safe_growth_zero_previous():
    result = safe_growth(Decimal("100"), Decimal("0"))
    assert result is None


# ------------------------------------------------------------------
# build_trend (shared helper)
# ------------------------------------------------------------------


def test_build_trend_empty():
    trend = build_trend([])
    assert trend.points == []
    assert trend.total == Decimal("0")
    assert trend.average == Decimal("0")
    assert trend.minimum == Decimal("0")
    assert trend.maximum == Decimal("0")
    assert trend.growth_pct is None


def test_build_trend_single_point():
    rows = [("2024-01", 100)]
    trend = build_trend(rows)
    assert len(trend.points) == 1
    assert trend.total == Decimal("100")
    assert trend.average == Decimal("100.00")
    assert trend.growth_pct is None  # needs >= 2 points


def test_build_trend_multiple():
    rows = [("2024-01", 100), ("2024-02", 200), ("2024-03", 150)]
    trend = build_trend(rows)
    assert len(trend.points) == 3
    assert trend.total == Decimal("450")
    assert trend.average == Decimal("150.00")
    assert trend.minimum == Decimal("100")
    assert trend.maximum == Decimal("200")
    # build_trend no longer calculates growth_pct — that is injected by
    # TrendRepository._inject_period_growth with proper period-over-period comparison
    assert trend.growth_pct is None


def test_safe_growth_negative():
    """Negative growth when current < previous."""
    result = safe_growth(Decimal("80"), Decimal("100"))
    assert result == Decimal("-20.00")


def test_safe_growth_equal():
    """Zero growth when current == previous."""
    result = safe_growth(Decimal("100"), Decimal("100"))
    assert result == Decimal("0.00")


def test_safe_growth_large_growth():
    """Large growth percentage is calculated correctly."""
    result = safe_growth(Decimal("1000"), Decimal("10"))
    assert result == Decimal("9900.00")


# ------------------------------------------------------------------
# build_ranking (shared helper)
# ------------------------------------------------------------------


def test_build_ranking_empty():
    result = build_ranking([])
    assert result.items == []
    assert result.total == Decimal("0")


def test_build_ranking_items():
    rows = [(1, "Product A", 500), (2, "Product B", 300), (3, "Product C", 200)]
    result = build_ranking(rows)
    assert len(result.items) == 3
    assert result.total == Decimal("1000")
    assert result.items[0].rank == 1
    assert result.items[0].name == "Product A"
    assert result.items[0].pct_of_total == Decimal("50.00")
    assert result.items[1].rank == 2
    assert result.items[2].pct_of_total == Decimal("20.00")


# ------------------------------------------------------------------
# get_kpi_summary (expanded with new fields)
# ------------------------------------------------------------------


def test_get_kpi_summary_no_data(analytics_repo, mock_session):
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = None
    mock_session.execute.return_value.fetchall.return_value = []
    result = analytics_repo.get_kpi_summary(date(2025, 1, 15))
    assert result.today_gross == Decimal("0")
    assert result.mtd_gross == Decimal("0")
    assert result.ytd_gross == Decimal("0")
    assert result.daily_transactions == 0
    assert result.daily_customers == 0
    assert result.avg_basket_size == Decimal("0")
    assert result.daily_returns == 0
    assert result.mtd_transactions == 0
    assert result.ytd_transactions == 0
    assert result.sparkline == []


def test_get_kpi_summary_with_data(analytics_repo, mock_session):
    # Unified CTE returns a single row as a named mapping
    unified_row = {
        "daily_gross_amount": 1000,
        "daily_discount": 0,
        "daily_quantity": 100,
        "mtd_gross_amount": 25000,
        "ytd_gross_amount": 300000,
        "daily_transactions": 42,
        "daily_unique_customers": 15,
        "daily_returns": 3,
        "mtd_transactions": 420,
        "ytd_transactions": 5000,
        "avg_basket_size": Decimal("595.24"),
        "prev_month_mtd": 20000,
        "prev_year_ytd": 250000,
    }
    sparkline_rows = [
        (date(2025, 6, 9), 800),
        (date(2025, 6, 10), 900),
        (date(2025, 6, 11), 1000),
    ]

    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = unified_row
    mock_session.execute.return_value.fetchall.return_value = sparkline_rows

    result = analytics_repo.get_kpi_summary(date(2025, 6, 15))
    assert result.today_gross == Decimal("1000")
    assert result.mtd_gross == Decimal("25000")
    assert result.ytd_gross == Decimal("300000")
    assert result.daily_transactions == 39  # 42 raw - 3 returns
    assert result.daily_customers == 15
    assert result.daily_returns == 3
    assert result.mtd_transactions == 420
    assert result.ytd_transactions == 5000
    assert result.avg_basket_size == Decimal("595.24")
    # MoM: (25000 - 20000) / 20000 * 100 = 25.00
    assert result.mom_growth_pct == Decimal("25.00")
    # YoY: (300000 - 250000) / 250000 * 100 = 20.00
    assert result.yoy_growth_pct == Decimal("20.00")


def test_get_kpi_summary_nulls_in_optional_fields(analytics_repo, mock_session):
    """CTE returns data but optional fields (basket, prev_month, prev_year) are NULL."""
    row = {
        "daily_gross_amount": 500,
        "daily_discount": None,
        "daily_quantity": None,
        "mtd_gross_amount": 1500,
        "ytd_gross_amount": 10000,
        "daily_transactions": 10,
        "daily_unique_customers": 5,
        "daily_returns": None,
        "mtd_transactions": None,
        "ytd_transactions": None,
        "avg_basket_size": None,
        "prev_month_mtd": None,
        "prev_year_ytd": None,
    }
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = row
    mock_session.execute.return_value.fetchall.return_value = []

    result = analytics_repo.get_kpi_summary(date(2025, 1, 1))
    assert result.today_gross == Decimal("500")
    assert result.daily_returns == 0
    assert result.mtd_transactions == 0
    assert result.ytd_transactions == 0
    assert result.avg_basket_size == Decimal("0")
    assert result.mom_growth_pct is None
    assert result.yoy_growth_pct is None
    assert result.sparkline == []


# ------------------------------------------------------------------
# get_kpi_summary_range via _get_kpi_from_fct_sales (dim-filter path)
# ------------------------------------------------------------------


def test_kpi_range_with_dim_filter_populates_mtd_ytd(analytics_repo, mock_session):
    """Dim-filter range path must populate mtd_gross / ytd_gross from dedicated
    CTEs — not zero them out. Regression test for the bug where any dashboard
    card reading mtd_gross while a category/brand/site/staff filter was active
    silently rendered $0.
    """
    row = {
        "period_net": Decimal("450000"),
        "total_quantity": Decimal("9200"),
        "total_transactions": 1800,
        "total_returns": 40,
        "total_customers": 620,
        "avg_basket_size": Decimal("255.56"),
        "prev_net": Decimal("400000"),
        # New fields from mtd_agg / ytd_agg CTEs
        "mtd_gross": Decimal("180000"),
        "mtd_transactions": 720,
        "ytd_gross": Decimal("2150000"),
        "ytd_transactions": 8600,
        "sparkline_points": None,
    }
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = row

    filters = AnalyticsFilter(
        date_range=DateRange(start_date=date(2025, 3, 10), end_date=date(2025, 3, 20)),
        category="Analgesic",  # Triggers the dim-filter path
    )
    result = analytics_repo.get_kpi_summary_range(filters)

    # Range-scoped fields — unchanged by this fix
    assert result.today_gross == Decimal("450000")
    assert result.daily_transactions == 1760  # 1800 - 40

    # The bug fix: MTD / YTD must NOT be zero when backend returns them
    assert result.mtd_gross == Decimal("180000")
    assert result.mtd_transactions == 720
    assert result.ytd_gross == Decimal("2150000")
    assert result.ytd_transactions == 8600


def test_kpi_range_with_dim_filter_null_mtd_ytd_defaults_to_zero(analytics_repo, mock_session):
    """If the MTD/YTD CTEs return NULL (e.g. no rows match in that window),
    repository must default to Decimal(0) / 0 — not crash.
    """
    row = {
        "period_net": Decimal("1000"),
        "total_quantity": Decimal("50"),
        "total_transactions": 10,
        "total_returns": 0,
        "total_customers": 8,
        "avg_basket_size": Decimal("125.00"),
        "prev_net": None,
        "mtd_gross": None,
        "mtd_transactions": None,
        "ytd_gross": None,
        "ytd_transactions": None,
        "sparkline_points": None,
    }
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = row

    filters = AnalyticsFilter(
        date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 1, 5)),
        site_key=42,
    )
    result = analytics_repo.get_kpi_summary_range(filters)

    assert result.mtd_gross == Decimal("0")
    assert result.ytd_gross == Decimal("0")
    assert result.mtd_transactions == 0
    assert result.ytd_transactions == 0


def test_get_filter_options(analytics_repo, mock_session):
    """UNION ALL filter options query returns mixed types correctly."""
    mock_session.execute.return_value.fetchall.return_value = [
        ("brand", "BrandA", None),
        ("brand", "BrandB", None),
        ("category", "Analgesic", None),
        ("site", "Cairo", 1),
        ("staff", "Ahmed", 10),
    ]
    result = analytics_repo.get_filter_options()
    assert len(result.brands) == 2
    assert len(result.categories) == 1
    assert len(result.sites) == 1
    assert result.sites[0].key == 1
    assert result.sites[0].label == "Cairo"
    assert len(result.staff) == 1
    assert result.staff[0].key == 10


def test_get_data_date_range(analytics_repo, mock_session):
    """Date range returns min/max from metrics_summary."""
    mock_session.execute.return_value.fetchone.return_value = (
        date(2023, 1, 1),
        date(2025, 12, 31),
    )
    min_d, max_d = analytics_repo.get_data_date_range()
    assert min_d == date(2023, 1, 1)
    assert max_d == date(2025, 12, 31)


def test_get_data_date_range_empty(analytics_repo, mock_session):
    """Date range returns None when no data."""
    mock_session.execute.return_value.fetchone.return_value = (None, None)
    min_d, max_d = analytics_repo.get_data_date_range()
    assert min_d is None
    assert max_d is None


# ------------------------------------------------------------------
# get_kpi_sparkline
# ------------------------------------------------------------------


def test_get_kpi_sparkline(analytics_repo, mock_session):
    mock_session.execute.return_value.fetchall.return_value = [
        (date(2025, 6, 9), 800),
        (date(2025, 6, 10), 900),
        (date(2025, 6, 11), 1000),
        (date(2025, 6, 12), 1100),
        (date(2025, 6, 13), 950),
        (date(2025, 6, 14), 1200),
        (date(2025, 6, 15), 1050),
    ]
    result = analytics_repo.get_kpi_sparkline(date(2025, 6, 15), days=7)
    assert len(result) == 7
    assert result[0].value == Decimal("800")
    assert result[6].value == Decimal("1050")


# ------------------------------------------------------------------
# get_daily_trend
# ------------------------------------------------------------------


def test_get_daily_trend(analytics_repo, mock_session):
    mock_session.execute.return_value.fetchall.return_value = [
        ("2025-01-01", 500),
        ("2025-01-02", 700),
    ]
    # Without date_range filters, _inject_period_growth returns None
    result = analytics_repo.get_daily_trend(AnalyticsFilter())
    assert len(result.points) == 2
    assert result.total == Decimal("1200")
    assert result.points[0].period == "2025-01-01"
    assert result.points[1].value == Decimal("700")
    # growth_pct is now period-over-period (requires date_range filter)
    # Without filters, no previous period can be queried → None
    assert result.growth_pct is None


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
