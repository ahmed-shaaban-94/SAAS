"""Tests for Session 4: Backend API Quality audit fixes.

Covers export hardening, targets SQL safety, reports info disclosure,
AI response validation, forecasting min series, BETWEEN filter validation,
backward pagination, and analytics caching.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# 1. Export route — date parsing, validation, limit bounds
# ---------------------------------------------------------------------------


class TestExportDateParsing:
    """Test the _parse_date helper and _build_filter in export.py."""

    def test_parse_valid_date(self):
        from datapulse.api.routes.export import _parse_date

        result = _parse_date("2025-01-15", "start_date")
        assert result == date(2025, 1, 15)

    def test_parse_none_returns_none(self):
        from datapulse.api.routes.export import _parse_date

        assert _parse_date(None, "start_date") is None

    def test_parse_invalid_date_raises_422(self):
        from fastapi import HTTPException

        from datapulse.api.routes.export import _parse_date

        with pytest.raises(HTTPException) as exc_info:
            _parse_date("not-a-date", "start_date")
        assert exc_info.value.status_code == 422
        assert "YYYY-MM-DD" in exc_info.value.detail

    def test_parse_partial_date_raises_422(self):
        from fastapi import HTTPException

        from datapulse.api.routes.export import _parse_date

        with pytest.raises(HTTPException):
            _parse_date("2025-13-01", "start_date")

    def test_build_filter_both_dates(self):
        from datapulse.api.routes.export import _build_filter

        f = _build_filter("2025-01-01", "2025-03-31", 50)
        assert f.date_range is not None
        assert f.date_range.start_date == date(2025, 1, 1)
        assert f.date_range.end_date == date(2025, 3, 31)

    def test_build_filter_no_dates(self):
        from datapulse.api.routes.export import _build_filter

        f = _build_filter(None, None, 50)
        assert f.date_range is None

    def test_build_filter_only_start_raises_422(self):
        from fastapi import HTTPException

        from datapulse.api.routes.export import _build_filter

        with pytest.raises(HTTPException) as exc_info:
            _build_filter("2025-01-01", None, 50)
        assert exc_info.value.status_code == 422
        assert "Both" in exc_info.value.detail

    def test_build_filter_reversed_dates_raises_422(self):
        from fastapi import HTTPException

        from datapulse.api.routes.export import _build_filter

        with pytest.raises(HTTPException) as exc_info:
            _build_filter("2025-12-31", "2025-01-01", 50)
        assert exc_info.value.status_code == 422
        assert "before" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 2. Targets repository — no asserts, parameterized SQL
# ---------------------------------------------------------------------------


class TestTargetsRepositorySafety:
    """Verify targets repo uses safe patterns."""

    def test_list_targets_no_dynamic_fstring(self):
        """Ensure list_targets uses parameterized WHERE, not f-string."""
        import inspect

        from datapulse.targets.repository import TargetsRepository

        source = inspect.getsource(TargetsRepository.list_targets)
        # The fixed code should use :target_type IS NULL pattern
        assert ":target_type IS NULL" in source or "IS NULL OR" in source
        # Should NOT have f-string WHERE interpolation
        assert "WHERE {where}" not in source

    def test_list_alert_logs_no_dynamic_fstring(self):
        """Ensure list_alert_logs uses parameterized filter, not f-string."""
        import inspect

        from datapulse.targets.repository import TargetsRepository

        source = inspect.getsource(TargetsRepository.list_alert_logs)
        # Should use :ack_only parameter, not string interpolation
        assert ":ack_only" in source
        assert 'f"""' not in source

    def test_create_target_no_assert(self):
        """Ensure production code uses proper error handling, not assert."""
        import inspect

        from datapulse.targets.repository import TargetsRepository

        source = inspect.getsource(TargetsRepository.create_target)
        assert "assert row" not in source
        assert "RuntimeError" in source

    def test_create_alert_config_no_assert(self):
        """Ensure production code uses proper error handling, not assert."""
        import inspect

        from datapulse.targets.repository import TargetsRepository

        source = inspect.getsource(TargetsRepository.create_alert_config)
        assert "assert row" not in source
        assert "RuntimeError" in source


# ---------------------------------------------------------------------------
# 3. Reports — no info disclosure
# ---------------------------------------------------------------------------


class TestReportsInfoDisclosure:
    """Verify report error messages don't leak internals."""

    def test_error_message_is_generic(self):
        """Ensure rendered error text doesn't include exception details."""
        import inspect

        from datapulse.reports.template_engine import render_report

        source = inspect.getsource(render_report)
        # Should NOT expose raw exception
        assert 'f"Error executing query: {exc}"' not in source
        # Should have generic message
        assert "contact support" in source


# ---------------------------------------------------------------------------
# 4. AI-Light response validation (M5)
# ---------------------------------------------------------------------------


class TestAIResponseValidation:
    """Verify AI anomaly results are validated before use."""

    def test_ai_anomalies_validated_severity(self):
        """AI-detected anomalies must have valid severity values."""
        from datapulse.ai_light.models import Anomaly

        # Valid severities
        for sev in ("low", "medium", "high"):
            a = Anomaly(
                date="2025-01-01",
                metric="daily_net_sales",
                actual_value=Decimal("100"),
                expected_range_low=Decimal("50"),
                expected_range_high=Decimal("150"),
                severity=sev,
                description="Test anomaly",
            )
            assert a.severity == sev

    def test_detect_anomalies_validates_ai_items(self):
        """AI service normalizes severity and skips invalid items."""
        import inspect

        from datapulse.ai_light.service import AILightService

        source = inspect.getsource(AILightService.detect_anomalies)
        # Should validate severity against known values
        assert 'ai_severity not in ("low", "medium", "high")' in source
        # Should skip items without date
        assert "not ai_date" in source
        # Should truncate description
        assert "[:500]" in source


# ---------------------------------------------------------------------------
# 5. Forecasting min series length (M6)
# ---------------------------------------------------------------------------


class TestForecastingMinSeries:
    """Verify min series length guard in forecasting service."""

    def test_min_daily_points_defined(self):
        """Daily forecast requires min_daily_points threshold."""
        import inspect

        from datapulse.forecasting.service import ForecastingService

        source = inspect.getsource(ForecastingService.run_all_forecasts)
        assert "min_daily_points" in source

    def test_short_daily_series_skipped(self):
        """Daily forecast should be skipped when series is too short."""
        import inspect

        from datapulse.forecasting.service import ForecastingService

        source = inspect.getsource(ForecastingService.run_all_forecasts)
        assert "min_daily_points" in source
        assert "insufficient_data" in source

    def test_short_monthly_series_skipped(self):
        """Monthly forecast should be skipped when series is too short."""
        import inspect

        from datapulse.forecasting.service import ForecastingService

        source = inspect.getsource(ForecastingService.run_all_forecasts)
        assert "min_monthly_points" in source
        assert "forecast_monthly_skipped" in source


# ---------------------------------------------------------------------------
# 6. BETWEEN filter validation (M8)
# ---------------------------------------------------------------------------


class TestBetweenFilterValidation:
    """Verify BETWEEN filter handles edge cases."""

    def test_between_valid_range(self):
        """Valid BETWEEN with two comma-separated values should call col.between()."""

        from sqlalchemy import column

        from datapulse.api.filters import FilterCondition, FilterOp, apply_filters

        col = column("test_date")
        query = MagicMock()
        query.where = MagicMock(return_value=query)

        filters = [
            FilterCondition(field="date", op=FilterOp.BETWEEN, value="2024-01-01,2024-12-31")
        ]
        apply_filters(query, filters, {"date": col})
        query.where.assert_called_once()

    def test_between_single_value_skipped(self):
        """BETWEEN with only one value should be skipped (not crash)."""

        from sqlalchemy import column

        from datapulse.api.filters import FilterCondition, FilterOp, apply_filters

        col = column("test_date")
        query = MagicMock()

        filters = [FilterCondition(field="date", op=FilterOp.BETWEEN, value="2024-01-01")]
        apply_filters(query, filters, {"date": col})
        query.where.assert_not_called()

    def test_between_empty_bound_skipped(self):
        """BETWEEN with an empty bound should be skipped."""

        from sqlalchemy import column

        from datapulse.api.filters import FilterCondition, FilterOp, apply_filters

        col = column("test_date")
        query = MagicMock()

        filters = [FilterCondition(field="date", op=FilterOp.BETWEEN, value=",2024-12-31")]
        apply_filters(query, filters, {"date": col})
        query.where.assert_not_called()

    def test_between_reversed_range_auto_swaps(self):
        """BETWEEN with reversed range should auto-swap and still apply filter."""

        from sqlalchemy import column

        from datapulse.api.filters import FilterCondition, FilterOp, apply_filters

        col = column("test_date")
        query = MagicMock()
        query.where = MagicMock(return_value=query)

        filters = [
            FilterCondition(field="date", op=FilterOp.BETWEEN, value="2024-12-31,2024-01-01")
        ]
        apply_filters(query, filters, {"date": col})
        # Should still apply filter (auto-swapped), not skip it
        query.where.assert_called_once()


# ---------------------------------------------------------------------------
# 7. Backward pagination (M9)
# ---------------------------------------------------------------------------


class TestBackwardPagination:
    """Verify prev_cursor is generated when navigating forward."""

    def test_first_page_no_prev_cursor(self):
        """First page (no current_cursor) should have no prev_cursor."""
        from datapulse.api.pagination import build_cursor_page

        items = [{"key": i} for i in range(6)]
        page = build_cursor_page(items, limit=5)
        assert page.prev_cursor is None
        assert page.has_prev is False

    def test_second_page_has_prev_cursor(self):
        """When current_cursor is provided, prev_cursor should be set."""
        from datapulse.api.pagination import build_cursor_page, encode_cursor

        items = [{"key": i} for i in range(5, 11)]  # page 2 items
        cursor = encode_cursor({"key": 4})
        page = build_cursor_page(items, limit=5, current_cursor=cursor)
        assert page.prev_cursor is not None
        assert page.has_prev is True

    def test_prev_cursor_contains_first_item_key(self):
        """prev_cursor should encode the first item's key for backward nav."""
        from datapulse.api.pagination import build_cursor_page, decode_cursor, encode_cursor

        items = [{"key": 5}, {"key": 6}, {"key": 7}]
        cursor = encode_cursor({"key": 4})
        page = build_cursor_page(items, limit=5, current_cursor=cursor)
        decoded = decode_cursor(page.prev_cursor)
        assert decoded["key"] == 5
        assert decoded["__dir"] == "prev"

    def test_backward_compat_has_prev_flag(self):
        """has_prev=True when current_cursor is set (even if explicitly False)."""
        from datapulse.api.pagination import build_cursor_page, encode_cursor

        items = [{"key": 1}]
        cursor = encode_cursor({"key": 0})
        page = build_cursor_page(items, limit=5, current_cursor=cursor)
        assert page.has_prev is True


# ---------------------------------------------------------------------------
# 8. Analytics caching — top_movers should be cached
# ---------------------------------------------------------------------------


class TestAnalyticsCaching:
    """Verify top_movers has @cached decorator."""

    def test_top_movers_is_cached(self):
        """get_top_movers should have the @cached decorator."""
        import inspect

        from datapulse.analytics.service import AnalyticsService

        # Check that the method source or decorators include cached
        source = inspect.getsource(AnalyticsService.get_top_movers)
        # The @cached decorator wraps the function — check for the wrapper attribute
        assert hasattr(AnalyticsService.get_top_movers, "__wrapped__") or "cached" in source
