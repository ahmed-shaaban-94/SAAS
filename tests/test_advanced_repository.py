"""Tests for advanced analytics repository — ABC, heatmap, returns trend, segments."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.advanced_repository import AdvancedRepository
from datapulse.analytics.models import AnalyticsFilter


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> AdvancedRepository:
    return AdvancedRepository(mock_session)


@pytest.fixture()
def default_filters() -> AnalyticsFilter:
    return AnalyticsFilter()


class TestABCAnalysis:
    def test_empty_result(self, repo: AdvancedRepository, mock_session: MagicMock, default_filters):
        mock_session.execute.return_value.fetchall.return_value = []
        result = repo.get_abc_analysis(default_filters)
        assert result.items == []
        assert result.total == Decimal("0")
        assert result.class_a_count == 0

    def test_with_data(self, repo: AdvancedRepository, mock_session: MagicMock, default_filters):
        mock_session.execute.return_value.fetchall.return_value = [
            (1, "Product A", Decimal("80000"), 1, Decimal("50.00"), Decimal("160000"), None),
            (2, "Product B", Decimal("40000"), 2, Decimal("75.00"), Decimal("160000"), None),
            (3, "Product C", Decimal("25000"), 3, Decimal("90.63"), Decimal("160000"), None),
            (4, "Product D", Decimal("15000"), 4, Decimal("100.00"), Decimal("160000"), None),
        ]
        result = repo.get_abc_analysis(default_filters, entity="product")
        assert len(result.items) == 4
        assert result.total == Decimal("160000")
        assert result.class_a_count >= 1

    def test_customer_entity(
        self, repo: AdvancedRepository, mock_session: MagicMock, default_filters
    ):
        mock_session.execute.return_value.fetchall.return_value = []
        result = repo.get_abc_analysis(default_filters, entity="customer")
        assert result.items == []


class TestHeatmapData:
    def test_empty_result(self, repo: AdvancedRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchall.return_value = []
        result = repo.get_heatmap_data(2025)
        assert result.cells == []
        assert result.min_value == Decimal("0")

    def test_with_data(self, repo: AdvancedRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchall.return_value = [
            ("2025-01-01", Decimal("5000")),
            ("2025-01-02", Decimal("8000")),
            ("2025-01-03", Decimal("3000")),
        ]
        result = repo.get_heatmap_data(2025)
        assert len(result.cells) == 3
        assert result.min_value == Decimal("3000")
        assert result.max_value == Decimal("8000")


class TestReturnsTrend:
    def test_empty_result(self, repo: AdvancedRepository, mock_session: MagicMock, default_filters):
        mock_session.execute.return_value.fetchall.return_value = []
        result = repo.get_returns_trend(default_filters)
        assert result.points == []
        assert result.total_returns == 0

    def test_with_data(self, repo: AdvancedRepository, mock_session: MagicMock, default_filters):
        mock_session.execute.return_value.fetchall.return_value = [
            ("2025-01", 50, Decimal("25000"), Decimal("2.50"), 2000),
            ("2025-02", 30, Decimal("15000"), Decimal("1.80"), 1667),
        ]
        result = repo.get_returns_trend(default_filters)
        assert len(result.points) == 2
        assert result.total_returns == 80
        assert result.total_return_amount == Decimal("40000")


class TestSegmentSummary:
    def test_empty_result(self, repo: AdvancedRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchall.return_value = []
        result = repo.get_segment_summary()
        assert result == []

    def test_with_data(self, repo: AdvancedRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchall.return_value = [
            ("Champions", 100, Decimal("500000"), Decimal("5000.00"), Decimal("10.50")),
            ("At Risk", 50, Decimal("100000"), Decimal("2000.00"), Decimal("3.20")),
        ]
        result = repo.get_segment_summary()
        assert len(result) == 2
        assert result[0].segment == "Champions"
        assert result[0].count == 100
        # pct_of_customers: 100/150 * 100 = 66.67
        assert result[0].pct_of_customers == Decimal("66.67")
