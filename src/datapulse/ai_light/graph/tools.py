"""LangGraph tool registry for the AI-Light graph (summary path, Phase A-2).

All tools are closure-bound to a per-request tenant-scoped SQLAlchemy session.
Each tool returns a plain dict (JSON-serializable) for state storage.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


def build_tool_registry(repo: AnalyticsRepository) -> list[Any]:
    """Return the list of LangGraph tools for the summary path.

    Tools are closure-bound to *repo* so they use the per-request RLS session.
    """
    from langchain_core.tools import tool  # lazy import — langchain_core is optional

    @tool
    def get_kpi_summary(target_date: str) -> dict[str, Any]:
        """Fetch KPI summary (gross sales, MTD, YTD, MoM/YoY growth) for a given date.

        Args:
            target_date: ISO date string, e.g. "2026-04-12".
        """
        parsed = date.fromisoformat(target_date)
        kpi = repo.get_kpi_summary(parsed)
        return kpi.model_dump(mode="json")

    @tool
    def get_daily_trend(start_date: str, end_date: str) -> dict[str, Any]:
        """Fetch daily net-sales trend for a date range.

        Args:
            start_date: ISO date string for the start of the period.
            end_date: ISO date string for the end of the period.
        """
        filters = AnalyticsFilter(
            date_range=DateRange(
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
            )
        )
        result = repo.get_daily_trend(filters)
        return result.model_dump(mode="json")

    @tool
    def get_monthly_trend(start_date: str, end_date: str) -> dict[str, Any]:
        """Fetch monthly net-sales trend for a date range.

        Args:
            start_date: ISO date string for the start of the period.
            end_date: ISO date string for the end of the period.
        """
        filters = AnalyticsFilter(
            date_range=DateRange(
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
            )
        )
        result = repo.get_monthly_trend(filters)
        return result.model_dump(mode="json")

    @tool
    def get_top_products(
        limit: int = 5, start_date: str = "", end_date: str = ""
    ) -> dict[str, Any]:
        """Fetch top-N products by net sales.

        Args:
            limit: Number of products to return (1-20).
            start_date: Optional ISO date string for the start of the period.
            end_date: Optional ISO date string for the end of the period.
        """
        date_range = None
        if start_date and end_date:
            date_range = DateRange(
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
            )
        filters = AnalyticsFilter(limit=min(max(limit, 1), 20), date_range=date_range)
        result = repo.get_top_products(filters)
        return result.model_dump(mode="json")

    @tool
    def get_top_customers(
        limit: int = 5, start_date: str = "", end_date: str = ""
    ) -> dict[str, Any]:
        """Fetch top-N customers by net sales.

        Args:
            limit: Number of customers to return (1-20).
            start_date: Optional ISO date string for the start of the period.
            end_date: Optional ISO date string for the end of the period.
        """
        date_range = None
        if start_date and end_date:
            date_range = DateRange(
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
            )
        filters = AnalyticsFilter(limit=min(max(limit, 1), 20), date_range=date_range)
        result = repo.get_top_customers(filters)
        return result.model_dump(mode="json")

    return [
        get_kpi_summary,
        get_daily_trend,
        get_monthly_trend,
        get_top_products,
        get_top_customers,
    ]
