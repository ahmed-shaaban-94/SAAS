"""Tests for the configurable quality engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from datapulse.pipeline.quality_engine import (
    CHECK_REGISTRY,
    DEFAULT_RULES,
    _check_custom_sql,
    _check_freshness,
    _check_null_rate,
    _check_row_count,
    run_configurable_checks,
)


class TestCheckRowCount:
    def test_passes_when_above_min(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 1000
        result = _check_row_count(session, "bronze", {"min_rows": 1})
        assert result.passed is True
        assert result.details["row_count"] == 1000

    def test_fails_when_below_min(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0
        result = _check_row_count(session, "bronze", {"min_rows": 1})
        assert result.passed is False

    def test_custom_min_rows(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 50
        result = _check_row_count(session, "bronze", {"min_rows": 100})
        assert result.passed is False
        assert result.details["min_rows"] == 100

    def test_unknown_stage(self):
        session = MagicMock()
        result = _check_row_count(session, "unknown_stage", {"min_rows": 1})
        assert result.passed is False
        assert "Unknown stage" in result.message


class TestCheckNullRate:
    def test_passes_when_below_threshold(self):
        session = MagicMock()
        # Return 0% null for all columns
        session.execute.return_value.fetchone.return_value = [0.0, 0.0, 0.0, 0.0]
        result = _check_null_rate(session, "bronze", {
            "threshold": 5.0,
            "columns": ["reference_no", "date", "net_sales", "quantity"],
        })
        assert result.passed is True

    def test_fails_when_above_threshold(self):
        session = MagicMock()
        # 10% null on first column
        session.execute.return_value.fetchone.return_value = [10.0, 0.0, 0.0, 0.0]
        result = _check_null_rate(session, "bronze", {
            "threshold": 5.0,
            "columns": ["reference_no", "date", "net_sales", "quantity"],
        })
        assert result.passed is False

    def test_custom_threshold(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = [8.0]
        result = _check_null_rate(session, "bronze", {
            "threshold": 10.0,
            "columns": ["reference_no"],
        })
        assert result.passed is True

    def test_unknown_stage(self):
        session = MagicMock()
        result = _check_null_rate(session, "unknown", {"columns": ["date"]})
        assert result.passed is False

    def test_filters_unsafe_columns(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = []
        result = _check_null_rate(session, "bronze", {
            "columns": ["DROP TABLE; --", "unsafe_col"],
        })
        # Should return True because no valid columns to check
        assert result.passed is True


class TestCheckFreshness:
    def test_passes_when_recent(self):
        from datetime import datetime, timedelta, timezone
        session = MagicMock()
        recent_date = datetime.now(timezone.utc) - timedelta(hours=1)
        session.execute.return_value.scalar_one.return_value = recent_date
        result = _check_freshness(session, "bronze", {"max_age_hours": 48, "date_column": "date"})
        assert result.passed is True

    def test_fails_when_stale(self):
        from datetime import datetime, timedelta, timezone
        session = MagicMock()
        old_date = datetime.now(timezone.utc) - timedelta(hours=100)
        session.execute.return_value.scalar_one.return_value = old_date
        result = _check_freshness(session, "bronze", {"max_age_hours": 48, "date_column": "date"})
        assert result.passed is False
        assert "hours old" in result.message

    def test_fails_when_no_data(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = None
        result = _check_freshness(session, "bronze", {"max_age_hours": 48, "date_column": "date"})
        assert result.passed is False

    def test_rejects_unsafe_date_column(self):
        session = MagicMock()
        result = _check_freshness(session, "bronze", {
            "max_age_hours": 48,
            "date_column": "DROP TABLE; --",
        })
        assert result.passed is False
        assert "Invalid date column" in result.message


class TestCheckCustomSQL:
    def test_passes_when_result_matches_expected(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0
        result = _check_custom_sql(session, "bronze", {
            "query": "SELECT COUNT(*) FROM bronze.sales WHERE quantity < 0",
            "expected": "0",
        })
        assert result.passed is True

    def test_fails_when_result_differs(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 42
        result = _check_custom_sql(session, "bronze", {
            "query": "SELECT COUNT(*) FROM bronze.sales WHERE quantity < 0",
            "expected": "0",
        })
        assert result.passed is False
        assert "Expected 0, got 42" in result.message

    def test_rejects_non_select_queries(self):
        session = MagicMock()
        result = _check_custom_sql(session, "bronze", {
            "query": "DELETE FROM bronze.sales",
            "expected": "0",
        })
        assert result.passed is False
        assert "SELECT" in result.message

    def test_handles_sql_error(self):
        session = MagicMock()
        session.execute.side_effect = Exception("syntax error")
        result = _check_custom_sql(session, "bronze", {
            "query": "SELECT invalid_syntax",
            "expected": "0",
        })
        assert result.passed is False
        assert "syntax error" in result.message


class TestRunConfigurableChecks:
    def test_uses_default_rules_when_none_provided(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 1000
        session.execute.return_value.fetchone.return_value = [0.0, 0.0, 0.0, 0.0]

        run_id = uuid4()
        report = run_configurable_checks(session, run_id, "bronze")

        assert report.pipeline_run_id == run_id
        assert report.stage == "bronze"
        assert len(report.checks) > 0

    def test_uses_custom_rules(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 500

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "error", "config": {"min_rows": 100}},
        ]
        report = run_configurable_checks(session, run_id, "gold", rules)

        assert len(report.checks) == 1
        assert report.checks[0].passed is True
        assert report.gate_passed is True

    def test_gate_passed_only_checks_errors(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 1000

        from datetime import datetime, timedelta, timezone
        old_date = datetime.now(timezone.utc) - timedelta(hours=100)
        session.execute.return_value.scalar_one.side_effect = [1000, old_date]

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "error", "config": {"min_rows": 1}},
            {"check_name": "freshness", "severity": "warn", "config": {"max_age_hours": 48, "date_column": "date"}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules)

        # row_count passes (error severity), freshness fails (warn severity)
        # gate_passed should be True (only error-severity checks matter)
        assert report.gate_passed is True
        assert report.all_passed is False

    def test_handles_unknown_check_name(self):
        session = MagicMock()
        run_id = uuid4()
        rules = [
            {"check_name": "nonexistent_check", "severity": "warn", "config": {}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules)

        assert len(report.checks) == 1
        assert report.checks[0].passed is False
        assert "Unknown check" in report.checks[0].message

    def test_handles_check_exception(self):
        session = MagicMock()
        session.execute.side_effect = Exception("DB down")

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "error", "config": {"min_rows": 1}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules)

        assert len(report.checks) == 1
        assert report.checks[0].passed is False
        assert "error" in report.checks[0].message.lower()

    def test_empty_rules_pass(self):
        session = MagicMock()
        run_id = uuid4()
        report = run_configurable_checks(session, run_id, "bronze", [])
        assert report.all_passed is True
        assert report.gate_passed is True

    def test_check_registry_has_all_checks(self):
        assert "row_count" in CHECK_REGISTRY
        assert "null_rate" in CHECK_REGISTRY
        assert "freshness" in CHECK_REGISTRY
        assert "custom_sql" in CHECK_REGISTRY

    def test_default_rules_exist_for_all_stages(self):
        assert "bronze" in DEFAULT_RULES
        assert "silver" in DEFAULT_RULES
        assert "gold" in DEFAULT_RULES
