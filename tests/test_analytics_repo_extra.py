"""Extra tests for AnalyticsRepository — covers uncovered lines in
get_monthly_trend (313-326), get_top_customers (340-341),
get_top_staff (350-351), get_site_performance (360-361),
and get_return_analysis (389 — empty results)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.repository import AnalyticsRepository


@pytest.fixture()
def repo():
    session = MagicMock()
    return AnalyticsRepository(session), session


class TestGetMonthlyTrend:
    def test_monthly_trend_returns_trend_result(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("2025-01", Decimal("50000")),
            ("2025-02", Decimal("60000")),
        ]
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_monthly_trend(filters)
        assert len(result.points) == 2
        assert result.points[0].period == "2025-01"

    def test_monthly_trend_empty(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_monthly_trend(filters)
        assert result.points == []


class TestGetTopCustomers:
    def test_top_customers_returns_ranking(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "Customer A", Decimal("100000")),
            (2, "Customer B", Decimal("80000")),
        ]
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_top_customers(filters)
        assert len(result.items) == 2
        assert result.items[0].name == "Customer A"


class TestGetTopStaff:
    def test_top_staff_returns_ranking(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (10, "Staff A", Decimal("70000")),
        ]
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_top_staff(filters)
        assert len(result.items) == 1


class TestGetSitePerformance:
    def test_site_performance_returns_ranking(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "Site Alpha", Decimal("200000")),
        ]
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_site_performance(filters)
        assert len(result.items) == 1
        assert result.items[0].name == "Site Alpha"


class TestGetReturnAnalysisEmpty:
    def test_return_analysis_empty(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_return_analysis(filters)
        assert result == []

    def test_return_analysis_with_data(self, repo):
        r, session = repo
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("Drug A", "Cust X", Decimal("5"), Decimal("-500.00"), 3),
        ]
        session.execute.return_value = mock_result

        filters = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31))
        )
        result = r.get_return_analysis(filters)
        assert len(result) == 1
        assert result[0].drug_name == "Drug A"
        assert result[0].return_count == 3
