"""Tests for analytics service layer."""

from datetime import date, timedelta
from decimal import Decimal

from datapulse.analytics.models import (
    AnalyticsFilter,
    DateRange,
    KPISummary,
    RankingItem,
    RankingResult,
    ReturnAnalysis,
    TimeSeriesPoint,
    TrendResult,
)


def test_default_filter_none(analytics_service, mock_repo):
    """When no filter is provided, returns a 30-day default."""
    max_date = date(2025, 3, 31)
    mock_repo.get_data_date_range.return_value = (date(2023, 1, 1), max_date)

    result = analytics_service._default_filter(None)

    assert result.date_range is not None
    assert result.date_range.start_date == max_date - timedelta(days=30)
    assert result.date_range.end_date == max_date


def test_default_filter_passthrough(analytics_service):
    """When a filter is provided, returns it unchanged."""
    custom_filter = AnalyticsFilter(
        date_range=DateRange(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        ),
        limit=5,
    )
    result = analytics_service._default_filter(custom_filter)
    assert result is custom_filter


def test_get_dashboard_summary_default_date(analytics_service, mock_repo):
    """Calls repo.get_kpi_summary with max date when none given."""
    max_date = date(2025, 3, 31)
    mock_repo.get_data_date_range.return_value = (date(2023, 1, 1), max_date)
    expected = KPISummary(
        today_gross=Decimal("500"),
        mtd_gross=Decimal("3000"),
        ytd_gross=Decimal("30000"),
        daily_transactions=20,
        daily_customers=10,
    )
    mock_repo.get_kpi_summary.return_value = expected

    result = analytics_service.get_dashboard_summary()

    mock_repo.get_kpi_summary.assert_called_once_with(max_date)
    assert result == expected


def test_get_dashboard_summary_custom_date(analytics_service, mock_repo):
    """Calls repo.get_kpi_summary with the specific date provided."""
    expected = KPISummary(
        today_gross=Decimal("1000"),
        mtd_gross=Decimal("5000"),
        ytd_gross=Decimal("50000"),
        daily_transactions=42,
        daily_customers=15,
    )
    mock_repo.get_kpi_summary.return_value = expected

    result = analytics_service.get_dashboard_summary(date(2025, 3, 15))

    mock_repo.get_kpi_summary.assert_called_once_with(date(2025, 3, 15))
    assert result == expected


def _make_trend_result() -> TrendResult:
    """Helper to build a minimal TrendResult for mocking."""
    return TrendResult(
        points=[TimeSeriesPoint(period="2025-01-01", value=Decimal("100"))],
        total=Decimal("100"),
        average=Decimal("100"),
        minimum=Decimal("100"),
        maximum=Decimal("100"),
    )


def _make_ranking_result() -> RankingResult:
    """Helper to build a minimal RankingResult for mocking."""
    return RankingResult(
        items=[
            RankingItem(
                rank=1,
                key=1,
                name="Item A",
                value=Decimal("500"),
                pct_of_total=Decimal("100"),
            ),
        ],
        total=Decimal("500"),
    )


def test_get_revenue_trends(analytics_service, mock_repo):
    """Calls both daily and monthly repo methods and returns dict with both keys."""
    daily = _make_trend_result()
    monthly = _make_trend_result()
    mock_repo.get_daily_trend.return_value = daily
    mock_repo.get_monthly_trend.return_value = monthly

    result = analytics_service.get_revenue_trends()

    mock_repo.get_daily_trend.assert_called_once()
    mock_repo.get_monthly_trend.assert_called_once()
    assert result == {"daily": daily, "monthly": monthly}


def test_get_product_insights(analytics_service, mock_repo):
    """Calls repo.get_top_products and returns the ranking."""
    expected = _make_ranking_result()
    mock_repo.get_top_products.return_value = expected

    result = analytics_service.get_product_insights()

    mock_repo.get_top_products.assert_called_once()
    assert result == expected


def test_get_customer_insights(analytics_service, mock_repo):
    """Calls repo.get_top_customers and returns the ranking."""
    expected = _make_ranking_result()
    mock_repo.get_top_customers.return_value = expected

    result = analytics_service.get_customer_insights()

    mock_repo.get_top_customers.assert_called_once()
    assert result == expected


def test_get_site_comparison(analytics_service, mock_repo):
    """Calls repo.get_site_performance and returns the ranking."""
    expected = _make_ranking_result()
    mock_repo.get_site_performance.return_value = expected

    result = analytics_service.get_site_comparison()

    mock_repo.get_site_performance.assert_called_once()
    assert result == expected


def test_get_staff_leaderboard(analytics_service, mock_repo):
    """Calls repo.get_top_staff and returns the ranking."""
    expected = _make_ranking_result()
    mock_repo.get_top_staff.return_value = expected

    result = analytics_service.get_staff_leaderboard()

    mock_repo.get_top_staff.assert_called_once()
    assert result == expected


def test_get_return_report(analytics_service, mock_repo):
    """Calls repo.get_return_analysis and returns the list."""
    expected = [
        ReturnAnalysis(
            drug_name="Drug X",
            customer_name="Customer A",
            return_quantity=Decimal("10"),
            return_amount=Decimal("250"),
            return_count=3,
        ),
    ]
    mock_repo.get_return_analysis.return_value = expected

    result = analytics_service.get_return_report()

    mock_repo.get_return_analysis.assert_called_once()
    assert result == expected
