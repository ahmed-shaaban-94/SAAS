"""Tests for AI-Light graph tool registry — each tool with a mocked AnalyticsRepository."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.models import AnalyticsFilter, RankingResult, TrendResult

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_kpi(**overrides):
    """Return a minimal KPISummary-like MagicMock."""
    kpi = MagicMock()
    kpi.model_dump.return_value = {
        "today_gross": 150000.0,
        "mtd_gross": 3000000.0,
        "ytd_gross": 12000000.0,
        "mom_growth_pct": 5.2,
        "yoy_growth_pct": 11.0,
        "daily_transactions": 120,
        "daily_customers": 95,
        **overrides,
    }
    return kpi


def _make_trend_result():
    trend = MagicMock(spec=TrendResult)
    trend.model_dump.return_value = {
        "points": [{"period": "2026-04-01", "value": 100.0}],
        "total": 100.0,
        "average": 100.0,
        "minimum": 100.0,
        "maximum": 100.0,
        "growth_pct": None,
    }
    return trend


def _make_ranking_result():
    ranking = MagicMock(spec=RankingResult)
    ranking.model_dump.return_value = {
        "items": [{"rank": 1, "name": "Item A", "value": 50000.0, "pct_of_total": 33.3}],
        "total": 50000.0,
    }
    return ranking


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.get_kpi_summary.return_value = _make_kpi()
    repo.get_daily_trend.return_value = _make_trend_result()
    repo.get_monthly_trend.return_value = _make_trend_result()
    repo.get_top_products.return_value = _make_ranking_result()
    repo.get_top_customers.return_value = _make_ranking_result()
    return repo


@pytest.fixture()
def tools(mock_repo):
    pytest.importorskip("langchain_core", reason="langchain_core not installed; skip tool tests")
    from datapulse.ai_light.graph.tools import build_tool_registry

    return build_tool_registry(mock_repo)


@pytest.fixture()
def tool_map(tools):
    return {t.name: t for t in tools}


# ---------------------------------------------------------------------------
# Tests: tool registry
# ---------------------------------------------------------------------------


class TestBuildToolRegistry:
    def test_returns_5_tools(self, tools):
        assert len(tools) == 5

    def test_tool_names(self, tool_map):
        expected = {
            "get_kpi_summary",
            "get_daily_trend",
            "get_monthly_trend",
            "get_top_products",
            "get_top_customers",
        }
        assert set(tool_map.keys()) == expected


# ---------------------------------------------------------------------------
# Tests: get_kpi_summary
# ---------------------------------------------------------------------------


class TestGetKpiSummary:
    def test_valid_date(self, tool_map, mock_repo):
        result = tool_map["get_kpi_summary"].invoke({"target_date": "2026-04-12"})
        mock_repo.get_kpi_summary.assert_called_once_with(date(2026, 4, 12))
        assert isinstance(result, dict)
        assert "today_gross" in result

    def test_invalid_date_raises(self, tool_map):
        with pytest.raises(ValueError):
            tool_map["get_kpi_summary"].invoke({"target_date": "not-a-date"})


# ---------------------------------------------------------------------------
# Tests: get_daily_trend
# ---------------------------------------------------------------------------


class TestGetDailyTrend:
    def test_calls_repo_with_filter(self, tool_map, mock_repo):
        result = tool_map["get_daily_trend"].invoke(
            {"start_date": "2026-03-01", "end_date": "2026-03-31"}
        )
        mock_repo.get_daily_trend.assert_called_once()
        call_arg = mock_repo.get_daily_trend.call_args[0][0]
        assert isinstance(call_arg, AnalyticsFilter)
        assert call_arg.date_range.start_date == date(2026, 3, 1)
        assert result["points"][0]["period"] == "2026-04-01"

    def test_invalid_dates_raise(self, tool_map):
        with pytest.raises(ValueError):
            tool_map["get_daily_trend"].invoke({"start_date": "bad", "end_date": "2026-03-31"})


# ---------------------------------------------------------------------------
# Tests: get_monthly_trend
# ---------------------------------------------------------------------------


class TestGetMonthlyTrend:
    def test_calls_repo(self, tool_map, mock_repo):
        result = tool_map["get_monthly_trend"].invoke(
            {"start_date": "2026-01-01", "end_date": "2026-03-31"}
        )
        mock_repo.get_monthly_trend.assert_called_once()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tests: get_top_products
# ---------------------------------------------------------------------------


class TestGetTopProducts:
    def test_default_limit(self, tool_map, mock_repo):
        tool_map["get_top_products"].invoke({"limit": 5})
        call_arg = mock_repo.get_top_products.call_args[0][0]
        assert call_arg.limit == 5

    def test_limit_clamped_to_max(self, tool_map, mock_repo):
        tool_map["get_top_products"].invoke({"limit": 999})
        call_arg = mock_repo.get_top_products.call_args[0][0]
        assert call_arg.limit == 20

    def test_limit_clamped_to_min(self, tool_map, mock_repo):
        tool_map["get_top_products"].invoke({"limit": 0})
        call_arg = mock_repo.get_top_products.call_args[0][0]
        assert call_arg.limit == 1

    def test_with_date_range(self, tool_map, mock_repo):
        tool_map["get_top_products"].invoke(
            {"limit": 5, "start_date": "2026-01-01", "end_date": "2026-03-31"}
        )
        call_arg = mock_repo.get_top_products.call_args[0][0]
        assert call_arg.date_range is not None
        assert call_arg.date_range.start_date == date(2026, 1, 1)

    def test_without_date_range(self, tool_map, mock_repo):
        tool_map["get_top_products"].invoke({"limit": 5})
        call_arg = mock_repo.get_top_products.call_args[0][0]
        assert call_arg.date_range is None


# ---------------------------------------------------------------------------
# Tests: get_top_customers
# ---------------------------------------------------------------------------


class TestGetTopCustomers:
    def test_basic_call(self, tool_map, mock_repo):
        result = tool_map["get_top_customers"].invoke({"limit": 5})
        mock_repo.get_top_customers.assert_called_once()
        assert isinstance(result, dict)

    def test_with_date_range(self, tool_map, mock_repo):
        tool_map["get_top_customers"].invoke(
            {"limit": 3, "start_date": "2026-01-01", "end_date": "2026-03-31"}
        )
        call_arg = mock_repo.get_top_customers.call_args[0][0]
        assert call_arg.date_range is not None
