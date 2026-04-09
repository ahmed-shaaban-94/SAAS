"""Tests for the configurable quality engine."""

from __future__ import annotations

import re
from datetime import UTC
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from datapulse.pipeline.quality_engine import (
    CHECK_REGISTRY,
    DEFAULT_RULES,
    _SAFE_IDENTIFIER_RE,
    _STAGE_TABLE,
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
        result = _check_null_rate(
            session,
            "bronze",
            {
                "threshold": 5.0,
                "columns": ["reference_no", "date", "net_sales", "quantity"],
            },
        )
        assert result.passed is True

    def test_fails_when_above_threshold(self):
        session = MagicMock()
        # 10% null on first column
        session.execute.return_value.fetchone.return_value = [10.0, 0.0, 0.0, 0.0]
        result = _check_null_rate(
            session,
            "bronze",
            {
                "threshold": 5.0,
                "columns": ["reference_no", "date", "net_sales", "quantity"],
            },
        )
        assert result.passed is False

    def test_custom_threshold(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = [8.0]
        result = _check_null_rate(
            session,
            "bronze",
            {
                "threshold": 10.0,
                "columns": ["reference_no"],
            },
        )
        assert result.passed is True

    def test_unknown_stage(self):
        session = MagicMock()
        result = _check_null_rate(session, "unknown", {"columns": ["date"]})
        assert result.passed is False

    def test_filters_unsafe_columns(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = []
        result = _check_null_rate(
            session,
            "bronze",
            {
                "columns": ["DROP TABLE; --", "unsafe_col"],
            },
        )
        # Should return True because no valid columns to check
        assert result.passed is True


class TestCheckFreshness:
    def test_passes_when_recent(self):
        from datetime import datetime, timedelta

        session = MagicMock()
        recent_date = datetime.now(UTC) - timedelta(hours=1)
        session.execute.return_value.scalar_one.return_value = recent_date
        result = _check_freshness(session, "bronze", {"max_age_hours": 48, "date_column": "date"})
        assert result.passed is True

    def test_fails_when_stale(self):
        from datetime import datetime, timedelta

        session = MagicMock()
        old_date = datetime.now(UTC) - timedelta(hours=100)
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
        result = _check_freshness(
            session,
            "bronze",
            {
                "max_age_hours": 48,
                "date_column": "DROP TABLE; --",
            },
        )
        assert result.passed is False
        assert "Invalid date column" in result.message


class TestCheckCustomSQL:
    def test_passes_when_result_matches_expected(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0
        result = _check_custom_sql(
            session,
            "bronze",
            {
                "query": "SELECT COUNT(*) FROM bronze.sales WHERE quantity < 0",
                "expected": "0",
            },
        )
        assert result.passed is True

    def test_fails_when_result_differs(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 42
        result = _check_custom_sql(
            session,
            "bronze",
            {
                "query": "SELECT COUNT(*) FROM bronze.sales WHERE quantity < 0",
                "expected": "0",
            },
        )
        assert result.passed is False
        assert "Expected 0, got 42" in result.message

    def test_rejects_non_select_queries(self):
        session = MagicMock()
        result = _check_custom_sql(
            session,
            "bronze",
            {
                "query": "DELETE FROM bronze.sales",
                "expected": "0",
            },
        )
        assert result.passed is False
        assert "SELECT" in result.message

    def test_handles_sql_error(self):
        session = MagicMock()
        session.execute.side_effect = Exception("syntax error")
        result = _check_custom_sql(
            session,
            "bronze",
            {
                "query": "SELECT invalid_syntax",
                "expected": "0",
            },
        )
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

        from datetime import datetime, timedelta

        old_date = datetime.now(UTC) - timedelta(hours=100)
        session.execute.return_value.scalar_one.side_effect = [1000, old_date]

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "error", "config": {"min_rows": 1}},
            {
                "check_name": "freshness",
                "severity": "warn",
                "config": {"max_age_hours": 48, "date_column": "date"},
            },
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


# ---------------------------------------------------------------------------
# T6.2 — Default rules loading
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaultRulesLoading:
    def test_bronze_has_row_count_and_null_rate(self):
        check_names = [r["check_name"] for r in DEFAULT_RULES["bronze"]]
        assert "row_count" in check_names
        assert "null_rate" in check_names

    def test_silver_has_null_rate_and_row_count(self):
        check_names = [r["check_name"] for r in DEFAULT_RULES["silver"]]
        assert "null_rate" in check_names
        assert "row_count" in check_names

    def test_gold_has_row_count(self):
        check_names = [r["check_name"] for r in DEFAULT_RULES["gold"]]
        assert "row_count" in check_names

    def test_all_rules_have_required_keys(self):
        for stage, rules in DEFAULT_RULES.items():
            for rule in rules:
                assert "check_name" in rule, f"Missing check_name in {stage}"
                assert "severity" in rule, f"Missing severity in {stage}"
                assert "config" in rule, f"Missing config in {stage}"

    def test_run_uses_defaults_when_rules_none(self):
        """Verify that run_configurable_checks with rules=None loads defaults for the stage."""
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 1000
        session.execute.return_value.fetchone.return_value = [0.0, 0.0, 0.0, 0.0]

        run_id = uuid4()
        report = run_configurable_checks(session, run_id, "bronze", rules=None)

        # Should have run bronze default rules (at least row_count + null_rate)
        check_names = [c.check_name for c in report.checks]
        assert "row_count" in check_names
        assert "null_rate" in check_names

    def test_unknown_stage_returns_empty_defaults(self):
        """A stage not in DEFAULT_RULES should run zero checks and pass."""
        session = MagicMock()
        run_id = uuid4()
        report = run_configurable_checks(session, run_id, "unknown_stage", rules=None)

        assert len(report.checks) == 0
        assert report.gate_passed is True
        assert report.all_passed is True


# ---------------------------------------------------------------------------
# T6.2 — Each check type
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckTypeRowCount:
    def test_exact_boundary_passes(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 1
        result = _check_row_count(session, "bronze", {"min_rows": 1})
        assert result.passed is True

    def test_silver_stage(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 500
        result = _check_row_count(session, "silver", {"min_rows": 1})
        assert result.passed is True
        assert result.stage == "silver"

    def test_gold_stage(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 10
        result = _check_row_count(session, "gold", {"min_rows": 1})
        assert result.passed is True
        assert result.stage == "gold"

    def test_default_min_rows_is_one(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 1
        result = _check_row_count(session, "bronze", {})
        assert result.passed is True


@pytest.mark.unit
class TestCheckTypeNullRate:
    def test_null_rate_with_none_fetchone(self):
        """When fetchone returns None (empty table), null pcts should be 0."""
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None
        result = _check_null_rate(
            session,
            "bronze",
            {"threshold": 5.0, "columns": ["reference_no"]},
        )
        # 0% null rate < 5% threshold => passes
        assert result.passed is True

    def test_threshold_at_exact_boundary_fails(self):
        """A null rate equal to threshold should fail (>= check)."""
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = [5.0]
        result = _check_null_rate(
            session,
            "bronze",
            {"threshold": 5.0, "columns": ["reference_no"]},
        )
        assert result.passed is False


@pytest.mark.unit
class TestCheckTypeDuplicateCheck:
    """Tests around the custom_sql check (used for duplicate detection among other things)."""

    def test_custom_sql_duplicate_check(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0
        result = _check_custom_sql(
            session,
            "bronze",
            {
                "query": "SELECT COUNT(*) - COUNT(DISTINCT reference_no) FROM bronze.sales",
                "expected": "0",
            },
        )
        assert result.passed is True

    def test_custom_sql_timeout(self):
        """Timeout errors should produce a descriptive message."""
        import sqlalchemy.exc

        session = MagicMock()
        session.execute.side_effect = sqlalchemy.exc.OperationalError(
            "statement", {}, Exception("canceling statement due to statement timeout")
        )
        result = _check_custom_sql(
            session,
            "bronze",
            {"query": "SELECT 1", "expected": "1", "timeout_ms": 1000},
        )
        assert result.passed is False
        assert "timed out" in result.message


# ---------------------------------------------------------------------------
# T6.2 — Custom rule override
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCustomRuleOverride:
    def test_custom_rules_replace_defaults(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 50

        run_id = uuid4()
        custom_rules = [
            {"check_name": "row_count", "severity": "warn", "config": {"min_rows": 10}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules=custom_rules)

        assert len(report.checks) == 1
        assert report.checks[0].check_name == "row_count"
        assert report.checks[0].severity == "warn"
        assert report.checks[0].passed is True

    def test_severity_override_from_rule(self):
        """The severity from the rule dict overrides the checker's default."""
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "warn", "config": {"min_rows": 1}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules=rules)

        # row_count fails but severity is warn, so gate should pass
        assert report.checks[0].passed is False
        assert report.checks[0].severity == "warn"
        assert report.gate_passed is True


# ---------------------------------------------------------------------------
# T6.2 — Severity levels (error blocks, warning passes)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSeverityLevels:
    def test_error_severity_blocks_gate(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "error", "config": {"min_rows": 1}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules=rules)

        assert report.checks[0].passed is False
        assert report.gate_passed is False

    def test_warn_severity_does_not_block_gate(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "warn", "config": {"min_rows": 1}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules=rules)

        assert report.checks[0].passed is False
        assert report.gate_passed is True
        assert report.all_passed is False

    def test_mixed_severities(self):
        """error passes + warn fails => gate_passed=True, all_passed=False."""
        session = MagicMock()
        # First call for row_count (passes), second for freshness (stale)
        from datetime import datetime, timedelta

        old_date = datetime.now(UTC) - timedelta(hours=100)
        session.execute.return_value.scalar_one.side_effect = [500, old_date]

        run_id = uuid4()
        rules = [
            {"check_name": "row_count", "severity": "error", "config": {"min_rows": 1}},
            {"check_name": "freshness", "severity": "warn", "config": {"max_age_hours": 24, "date_column": "date"}},
        ]
        report = run_configurable_checks(session, run_id, "bronze", rules=rules)

        assert report.gate_passed is True
        assert report.all_passed is False


# ---------------------------------------------------------------------------
# T6.2 — Safe identifier regex
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSafeIdentifierRegex:
    @pytest.mark.parametrize(
        "identifier",
        ["date", "net_sales", "reference_no", "a123", "col_name_2"],
    )
    def test_valid_identifiers(self, identifier: str):
        assert _SAFE_IDENTIFIER_RE.match(identifier) is not None

    @pytest.mark.parametrize(
        "identifier",
        [
            "DROP TABLE;--",
            "1starts_with_digit",
            "UPPER_CASE",
            "with space",
            "with-dash",
            "",
            "col.name",
        ],
    )
    def test_invalid_identifiers(self, identifier: str):
        assert _SAFE_IDENTIFIER_RE.match(identifier) is None


# ---------------------------------------------------------------------------
# T6.2 — Empty table edge case
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmptyTableEdgeCase:
    def test_row_count_zero_fails(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = 0
        result = _check_row_count(session, "bronze", {"min_rows": 1})
        assert result.passed is False
        assert "0 rows" in result.message

    def test_null_rate_empty_table(self):
        """When table is empty, null pcts should default to 0 and pass."""
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None
        result = _check_null_rate(
            session,
            "bronze",
            {"threshold": 5.0, "columns": ["reference_no", "date"]},
        )
        assert result.passed is True

    def test_freshness_no_data(self):
        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = None
        result = _check_freshness(
            session,
            "bronze",
            {"max_age_hours": 48, "date_column": "date"},
        )
        assert result.passed is False
        assert "No data found" in result.message

    def test_empty_rules_list_passes_gate(self):
        session = MagicMock()
        run_id = uuid4()
        report = run_configurable_checks(session, run_id, "bronze", rules=[])
        assert report.gate_passed is True
        assert report.all_passed is True
        assert len(report.checks) == 0


# ---------------------------------------------------------------------------
# T6.2 — Stage table mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStageTableMapping:
    def test_all_known_stages_mapped(self):
        assert "bronze" in _STAGE_TABLE
        assert "silver" in _STAGE_TABLE
        assert "gold" in _STAGE_TABLE

    def test_stage_table_values(self):
        assert _STAGE_TABLE["bronze"] == ("bronze", "sales")
        assert _STAGE_TABLE["silver"] == ("public_staging", "stg_sales")
        assert _STAGE_TABLE["gold"] == ("public_marts", "fct_sales")
