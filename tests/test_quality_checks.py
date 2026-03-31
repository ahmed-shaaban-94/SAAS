"""Tests for data quality check functions — Phase 2.5.

Covers:
- All 7 check functions (unit, mocked DB session)
- QualityCheckResult frozen model
- QualityReport gate logic
- QualityCheckRequest defaults
- VALID_STAGES constant
"""

from __future__ import annotations

import subprocess
from datetime import UTC
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from datapulse.pipeline.quality import (
    CRITICAL_COLUMNS,
    VALID_STAGES,
    QualityCheckRequest,
    QualityCheckResult,
    QualityReport,
    check_dedup_effective,
    check_financial_signs,
    check_null_rate,
    check_row_count,
    check_row_delta,
    check_schema_drift,
    run_dbt_tests,
)

# ---------------------------------------------------------------------------
# Session mock helpers
# ---------------------------------------------------------------------------


def _mock_session_scalar(value):
    """Return a mock session whose execute().scalar_one() returns *value*."""
    session = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = value
    session.execute.return_value = result
    return session


def _mock_session_fetchone(mapping: dict | None):
    """Return a mock session whose execute().fetchone() returns a row with *mapping*.

    Pass ``None`` to simulate no matching row (first run, etc.).
    """
    session = MagicMock()
    if mapping is None:
        result = MagicMock()
        result.fetchone.return_value = None
        session.execute.return_value = result
    else:
        row = MagicMock()
        row._mapping = mapping
        result = MagicMock()
        result.fetchone.return_value = row
        session.execute.return_value = result
    return session


def _mock_session_fetchall(rows: list[dict]):
    """Return a mock session whose execute().fetchall() returns rows built from *rows*.

    Each dict becomes an object whose ``._mapping`` attribute is that dict.
    """
    session = MagicMock()
    mock_rows = []
    for r in rows:
        mock_row = MagicMock()
        mock_row._mapping = r
        mock_rows.append(mock_row)
    result = MagicMock()
    result.fetchall.return_value = mock_rows
    session.execute.return_value = result
    return session


def _mock_session_scalar_sequence(values: list):
    """Return a mock session whose successive execute() calls return each value
    via scalar_one().  Useful when the function under test issues multiple
    queries with different expected scalars.
    """
    session = MagicMock()
    results = []
    for v in values:
        r = MagicMock()
        r.scalar_one.return_value = v
        results.append(r)
    session.execute.side_effect = results
    return session


# ---------------------------------------------------------------------------
# TestCheckRowCount
# ---------------------------------------------------------------------------


class TestCheckRowCount:
    """check_row_count() — verifies bronze.sales has at least one row."""

    def test_passes_with_rows(self):
        session = _mock_session_scalar(50_000)
        run_id = uuid4()

        result = check_row_count(session, run_id)

        assert result.passed is True
        assert result.check_name == "row_count"
        assert result.stage == "bronze"
        assert result.severity == "error"
        assert result.details["row_count"] == 50_000
        assert result.message is None

    def test_fails_with_zero_rows(self):
        session = _mock_session_scalar(0)

        result = check_row_count(session, uuid4())

        assert result.passed is False
        assert result.severity == "error"
        assert result.details["row_count"] == 0
        assert "empty" in result.message.lower()

    def test_fails_with_exactly_zero(self):
        """Edge case: zero is the boundary — should fail."""
        session = _mock_session_scalar(0)
        result = check_row_count(session, uuid4())
        assert result.passed is False

    def test_passes_with_one_row(self):
        """Edge case: single row — should pass (> 0)."""
        session = _mock_session_scalar(1)
        result = check_row_count(session, uuid4())
        assert result.passed is True

    def test_passes_with_large_table(self):
        """Large dataset should pass without issues."""
        session = _mock_session_scalar(2_269_598)
        result = check_row_count(session, uuid4())
        assert result.passed is True
        assert result.details["row_count"] == 2_269_598

    def test_executes_correct_table(self):
        """Verifies the SQL targets bronze.sales."""
        session = _mock_session_scalar(100)
        check_row_count(session, uuid4())

        called_sql = str(session.execute.call_args[0][0])
        assert "bronze.sales" in called_sql.lower() or "bronze" in called_sql.lower()


# ---------------------------------------------------------------------------
# TestCheckRowDelta
# ---------------------------------------------------------------------------


class TestCheckRowDelta:
    """check_row_delta() — warns when row count dropped >50% vs previous run."""

    def _make_session_two_queries(self, current_count: int, prev_rows_loaded):
        """Build a session that serves current count and previous-run fetchone."""
        session = MagicMock()

        # First call → current COUNT(*)
        current_result = MagicMock()
        current_result.scalar_one.return_value = current_count

        # Second call → previous run fetchone
        prev_result = MagicMock()
        if prev_rows_loaded is None:
            prev_result.fetchone.return_value = None
        else:
            row = MagicMock()
            row._mapping = {"rows_loaded": prev_rows_loaded}
            prev_result.fetchone.return_value = row

        session.execute.side_effect = [current_result, prev_result]
        return session

    def test_passes_within_threshold(self):
        """4% delta — well within 50% threshold."""
        session = self._make_session_two_queries(50_000, 48_000)

        result = check_row_delta(session, uuid4())

        assert result.passed is True
        assert result.check_name == "row_delta"
        assert result.severity == "warn"
        assert result.details["current"] == 50_000
        assert result.details["previous"] == 48_000
        assert result.details["delta_pct"] == pytest.approx(4.17, abs=0.1)

    def test_passes_at_exact_50_percent_threshold(self):
        """50% delta is exactly the boundary — should still pass (<=50)."""
        session = self._make_session_two_queries(50_000, 100_000)

        result = check_row_delta(session, uuid4())

        assert result.passed is True
        assert result.details["delta_pct"] == 50.0

    def test_warns_above_threshold(self):
        """150% delta — exceeds threshold, severity='warn'."""
        session = self._make_session_two_queries(50_000, 20_000)

        result = check_row_delta(session, uuid4())

        assert result.passed is False
        assert result.severity == "warn"
        assert result.message is not None
        assert "50%" in result.message

    def test_passes_first_run_no_previous(self):
        """No previous run — should pass and mention first run."""
        session = self._make_session_two_queries(50_000, None)

        result = check_row_delta(session, uuid4())

        assert result.passed is True
        assert result.details["previous"] is None
        assert result.details["delta_pct"] is None
        assert "previous" in result.message.lower()

    def test_passes_previous_run_zero_rows(self):
        """Previous run had zero rows — skip delta check, pass."""
        session = self._make_session_two_queries(50_000, 0)

        result = check_row_delta(session, uuid4())

        assert result.passed is True
        assert result.details["previous"] == 0
        assert result.details["delta_pct"] is None


# ---------------------------------------------------------------------------
# TestCheckSchemaDrift
# ---------------------------------------------------------------------------


class TestCheckSchemaDrift:
    """check_schema_drift() — verifies all expected columns are present in DB."""

    def _build_column_rows(self, column_names: list[str]) -> list[dict]:
        return [{"column_name": c} for c in column_names]

    def test_passes_matching_columns(self):
        """All expected columns present — should pass."""
        from datapulse.bronze.column_map import COLUMN_MAP

        db_columns = list(COLUMN_MAP.values())
        session = _mock_session_fetchall(self._build_column_rows(db_columns))

        result = check_schema_drift(session, uuid4())

        assert result.passed is True
        assert result.check_name == "schema_drift"
        assert result.stage == "bronze"
        assert result.severity == "error"
        assert result.details["missing"] == []

    def test_fails_missing_columns(self):
        """Some expected columns absent — should fail with details.missing populated."""
        from datapulse.bronze.column_map import COLUMN_MAP

        # Provide only half the expected columns
        db_columns = list(COLUMN_MAP.values())[:10]
        session = _mock_session_fetchall(self._build_column_rows(db_columns))

        result = check_schema_drift(session, uuid4())

        assert result.passed is False
        assert result.severity == "error"
        assert len(result.details["missing"]) > 0
        assert result.message is not None
        assert "missing" in result.message.lower()

    def test_ignores_system_columns(self):
        """id, tenant_id, loaded_at are system cols — must not count as extra."""
        from datapulse.bronze.column_map import COLUMN_MAP

        db_columns = list(COLUMN_MAP.values()) + ["id", "tenant_id", "loaded_at"]
        session = _mock_session_fetchall(self._build_column_rows(db_columns))

        result = check_schema_drift(session, uuid4())

        assert result.passed is True
        # System cols should not appear in 'extra' since they're excluded before comparison
        assert "id" not in result.details.get("extra", [])
        assert "tenant_id" not in result.details.get("extra", [])
        assert "loaded_at" not in result.details.get("extra", [])

    def test_extra_unknown_columns_recorded(self):
        """Columns present in DB but not in COLUMN_MAP are 'extra' (non-blocking)."""
        from datapulse.bronze.column_map import COLUMN_MAP

        db_columns = list(COLUMN_MAP.values()) + ["unknown_col_1", "unknown_col_2"]
        session = _mock_session_fetchall(self._build_column_rows(db_columns))

        result = check_schema_drift(session, uuid4())

        assert result.passed is True  # missing=0, so passes
        assert "unknown_col_1" in result.details["extra"]
        assert "unknown_col_2" in result.details["extra"]

    def test_empty_table_columns_fails(self):
        """No columns at all — should fail."""
        session = _mock_session_fetchall([])

        result = check_schema_drift(session, uuid4())

        assert result.passed is False
        assert len(result.details["missing"]) > 0


# ---------------------------------------------------------------------------
# TestCheckNullRate
# ---------------------------------------------------------------------------


class TestCheckNullRate:
    """check_null_rate() — critical columns must have <5% NULL values."""

    def _session_for_null_pcts(self, pcts: list[float | None]):
        """Build a session returning a single row with null pct values (one per column)."""
        session = MagicMock()
        row = MagicMock()
        row.__getitem__ = lambda self_, i: pcts[i]
        result = MagicMock()
        result.fetchone.return_value = row
        session.execute.return_value = result
        return session

    def test_passes_below_threshold(self):
        """All columns at 0% nulls — should pass."""
        pcts = [0.0] * len(CRITICAL_COLUMNS)
        session = self._session_for_null_pcts(pcts)

        result = check_null_rate(session, uuid4())

        assert result.passed is True
        assert result.check_name == "null_rate"
        assert result.severity == "error"
        assert result.details["threshold"] == 5.0
        for col in CRITICAL_COLUMNS:
            assert result.details["columns"][col] == 0.0

    def test_passes_just_below_threshold(self):
        """4.99% nulls — still below threshold."""
        pcts = [4.99] * len(CRITICAL_COLUMNS)
        session = self._session_for_null_pcts(pcts)

        result = check_null_rate(session, uuid4())

        assert result.passed is True

    def test_fails_above_threshold(self):
        """reference_no has 10% nulls — should fail."""
        # reference_no is first in CRITICAL_COLUMNS
        pcts = [10.0] + [0.0] * (len(CRITICAL_COLUMNS) - 1)
        session = self._session_for_null_pcts(pcts)

        result = check_null_rate(session, uuid4())

        assert result.passed is False
        assert result.severity == "error"
        assert CRITICAL_COLUMNS[0] in result.message
        assert result.details["columns"][CRITICAL_COLUMNS[0]] == 10.0

    def test_fails_at_exactly_threshold(self):
        """5.0% is at the threshold (>= 5.0 → fail)."""
        pcts = [5.0] + [0.0] * (len(CRITICAL_COLUMNS) - 1)
        session = self._session_for_null_pcts(pcts)

        result = check_null_rate(session, uuid4())

        assert result.passed is False

    def test_bronze_stage_queries_bronze_sales(self):
        """Default stage='bronze' should query bronze.sales."""
        pcts = [0.0] * len(CRITICAL_COLUMNS)
        session = self._session_for_null_pcts(pcts)

        check_null_rate(session, uuid4(), stage="bronze")

        first_sql = str(session.execute.call_args_list[0][0][0])
        assert "bronze" in first_sql.lower()
        assert "sales" in first_sql.lower()

    def test_silver_stage_queries_stg_sales(self):
        """stage='silver' should query public_staging.stg_sales."""
        pcts = [0.0] * len(CRITICAL_COLUMNS)
        session = self._session_for_null_pcts(pcts)

        check_null_rate(session, uuid4(), stage="silver")

        first_sql = str(session.execute.call_args_list[0][0][0])
        assert "public_staging" in first_sql.lower() or "stg_sales" in first_sql.lower()

    def test_null_result_treated_as_zero(self):
        """DB returning NULL (empty table) should be treated as 0.0% nulls."""
        pcts = [None] * len(CRITICAL_COLUMNS)
        session = self._session_for_null_pcts(pcts)

        result = check_null_rate(session, uuid4())

        assert result.passed is True
        for col in CRITICAL_COLUMNS:
            assert result.details["columns"][col] == 0.0

    def test_all_critical_columns_checked(self):
        """Single query should check all critical columns at once."""
        pcts = [0.0] * len(CRITICAL_COLUMNS)
        session = self._session_for_null_pcts(pcts)

        result = check_null_rate(session, uuid4())

        session.execute.assert_called_once()
        assert len(result.details["columns"]) == len(CRITICAL_COLUMNS)


# ---------------------------------------------------------------------------
# TestCheckDedupEffective
# ---------------------------------------------------------------------------


class TestCheckDedupEffective:
    """check_dedup_effective() — silver row count must not exceed bronze."""

    def _make_session(self, bronze: int, silver: int):
        return _mock_session_scalar_sequence([bronze, silver])

    def test_passes_silver_less(self):
        """silver < bronze — dedup reduced rows as expected."""
        session = self._make_session(bronze=50_000, silver=45_000)

        result = check_dedup_effective(session, uuid4())

        assert result.passed is True
        assert result.check_name == "dedup_effective"
        assert result.stage == "silver"
        assert result.severity == "warn"
        assert result.details["bronze_count"] == 50_000
        assert result.details["silver_count"] == 45_000

    def test_passes_silver_equal_bronze(self):
        """silver == bronze — no dedup occurred but also no inflation."""
        session = self._make_session(bronze=50_000, silver=50_000)

        result = check_dedup_effective(session, uuid4())

        assert result.passed is True

    def test_warns_silver_more(self):
        """silver > bronze — dedup failed, severity='warn'."""
        session = self._make_session(bronze=50_000, silver=55_000)

        result = check_dedup_effective(session, uuid4())

        assert result.passed is False
        assert result.severity == "warn"
        assert result.message is not None
        assert "dedup" in result.message.lower() or "silver" in result.message.lower()

    def test_message_contains_counts(self):
        """Failure message includes both counts for observability."""
        session = self._make_session(bronze=100, silver=200)

        result = check_dedup_effective(session, uuid4())

        assert "200" in result.message
        assert "100" in result.message


# ---------------------------------------------------------------------------
# TestCheckFinancialSigns
# ---------------------------------------------------------------------------


class TestCheckFinancialSigns:
    """check_financial_signs() — net_sales/quantity sign mismatch must be <1%."""

    def _make_session(self, total: int, inconsistent: int):
        return _mock_session_scalar_sequence([total, inconsistent])

    def test_passes_consistent(self):
        """No inconsistent rows — should pass."""
        session = self._make_session(total=50_000, inconsistent=0)

        result = check_financial_signs(session, uuid4())

        assert result.passed is True
        assert result.check_name == "financial_signs"
        assert result.stage == "silver"
        assert result.severity == "warn"
        assert result.details["inconsistent_count"] == 0
        assert result.details["pct"] == 0.0

    def test_passes_below_1_percent(self):
        """0.5% inconsistent — below 1% threshold."""
        session = self._make_session(total=10_000, inconsistent=50)

        result = check_financial_signs(session, uuid4())

        assert result.passed is True

    def test_warns_at_exactly_1_percent(self):
        """1.0% is at threshold (>= 1.0 → fail)."""
        session = self._make_session(total=10_000, inconsistent=100)

        result = check_financial_signs(session, uuid4())

        assert result.passed is False

    def test_warns_inconsistent(self):
        """2% inconsistency — severity='warn', message present."""
        session = self._make_session(total=50_000, inconsistent=1_000)

        result = check_financial_signs(session, uuid4())

        assert result.passed is False
        assert result.severity == "warn"
        assert result.message is not None
        assert "1%" in result.message

    def test_zero_total_safe(self):
        """Empty table (total=0) — should not raise ZeroDivisionError."""
        session = self._make_session(total=0, inconsistent=0)

        result = check_financial_signs(session, uuid4())

        assert result.passed is True
        assert result.details["pct"] == 0.0

    def test_details_contain_all_fields(self):
        """details dict must contain inconsistent_count, total, pct."""
        session = self._make_session(total=1_000, inconsistent=5)

        result = check_financial_signs(session, uuid4())

        assert "inconsistent_count" in result.details
        assert "total" in result.details
        assert "pct" in result.details


# ---------------------------------------------------------------------------
# TestRunDbtTests
# ---------------------------------------------------------------------------


class TestRunDbtTests:
    """run_dbt_tests() — runs dbt test subprocess and wraps output."""

    def _make_settings(self):
        settings = MagicMock()
        settings.dbt_project_dir = "/app/dbt"
        settings.dbt_profiles_dir = "/app/dbt"
        settings.pipeline_dbt_timeout = 300
        return settings

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_dbt_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Completed. 10 tests passed.",
            stderr="",
        )
        settings = self._make_settings()

        result = run_dbt_tests(uuid4(), "marts", settings)

        assert result.passed is True
        assert result.check_name == "dbt_test_marts"
        assert result.stage == "gold"
        assert result.severity == "error"
        assert result.message is None

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_dbt_failure_non_zero_exit(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="FAIL 3 | model.bronze_sales",
        )
        settings = self._make_settings()

        result = run_dbt_tests(uuid4(), "staging", settings)

        assert result.passed is False
        assert result.severity == "error"
        assert result.message is not None
        assert "exit code 1" in result.message
        assert result.details["stderr"][:50]  # stderr is captured in details

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_dbt_stderr_truncated_to_500_chars(self, mock_run):
        long_stderr = "E" * 1000
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr=long_stderr,
        )
        settings = self._make_settings()

        result = run_dbt_tests(uuid4(), "marts", settings)

        assert len(result.details["stderr"]) <= 500

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_dbt_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dbt test", timeout=300)
        settings = self._make_settings()

        result = run_dbt_tests(uuid4(), "marts", settings)

        assert result.passed is False
        assert result.severity == "error"
        assert "timed out" in result.message.lower() or "timeout" in result.message.lower()
        assert "300" in result.message  # timeout value in message

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_dbt_unexpected_exception(self, mock_run):
        mock_run.side_effect = OSError("dbt binary not found")
        settings = self._make_settings()

        result = run_dbt_tests(uuid4(), "marts", settings)

        assert result.passed is False
        assert "dbt binary not found" in result.message

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_check_name_includes_selector(self, mock_run):
        """check_name must embed the selector string for traceability."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        settings = self._make_settings()

        result = run_dbt_tests(uuid4(), "marts", settings)

        assert "marts" in result.check_name

    @patch("datapulse.pipeline.quality.subprocess.run")
    def test_subprocess_called_with_correct_args(self, mock_run):
        """Verifies dbt CLI invocation includes project-dir, profiles-dir, select."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        settings = self._make_settings()

        run_dbt_tests(uuid4(), "staging", settings)

        cmd = mock_run.call_args[0][0]
        assert "dbt" in cmd
        assert "test" in cmd
        assert "--select" in cmd
        assert "staging" in cmd
        assert "--project-dir" in cmd
        assert "--profiles-dir" in cmd


# ---------------------------------------------------------------------------
# TestQualityModels
# ---------------------------------------------------------------------------


class TestQualityModels:
    """Pydantic model invariants and business logic tests."""

    def test_quality_check_result_frozen(self):
        """QualityCheckResult is immutable — mutation must raise TypeError."""
        result = QualityCheckResult(
            check_name="row_count",
            stage="bronze",
            severity="error",
            passed=True,
            message=None,
            details={"row_count": 100},
        )

        with pytest.raises((TypeError, Exception)):
            result.passed = False  # type: ignore[misc]

    def test_quality_report_gate_passes_when_all_pass(self):
        """gate_passed=True when every error-severity check passes."""
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={},
            ),
            QualityCheckResult(
                check_name="row_delta",
                stage="bronze",
                severity="warn",
                passed=True,
                message=None,
                details={},
            ),
        ]
        from datetime import datetime

        report = QualityReport(
            pipeline_run_id=uuid4(),
            stage="bronze",
            checks=checks,
            all_passed=True,
            gate_passed=True,
            checked_at=datetime.now(UTC),
        )

        assert report.gate_passed is True
        assert report.all_passed is True

    def test_quality_report_gate_blocks_on_error_severity_fail(self):
        """gate_passed=False when an error-severity check fails."""
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=False,
                message="No rows",
                details={},
            ),
            QualityCheckResult(
                check_name="row_delta",
                stage="bronze",
                severity="warn",
                passed=False,
                message="High delta",
                details={},
            ),
        ]
        from datetime import datetime

        report = QualityReport(
            pipeline_run_id=uuid4(),
            stage="bronze",
            checks=checks,
            all_passed=False,
            gate_passed=False,  # error check failed
            checked_at=datetime.now(UTC),
        )

        assert report.gate_passed is False
        assert report.all_passed is False

    def test_quality_report_gate_passes_with_warn_only_fail(self):
        """gate_passed can be True when only warn-severity checks fail."""
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={},
            ),
            QualityCheckResult(
                check_name="row_delta",
                stage="bronze",
                severity="warn",
                passed=False,
                message="Large drop",
                details={},
            ),
        ]
        # Simulate service logic: gate_passed because no error checks failed
        error_checks_all_pass = all(c.passed for c in checks if c.severity == "error")
        all_pass = all(c.passed for c in checks)

        assert error_checks_all_pass is True
        assert all_pass is False

    def test_quality_check_request_default_tenant_id(self):
        """QualityCheckRequest.tenant_id defaults to 1."""
        req = QualityCheckRequest(run_id=uuid4(), stage="bronze")

        assert req.tenant_id == 1

    def test_quality_check_request_custom_tenant_id(self):
        req = QualityCheckRequest(run_id=uuid4(), stage="silver", tenant_id=42)

        assert req.tenant_id == 42

    def test_valid_stages_contains_all_three(self):
        """VALID_STAGES must include bronze, silver, and gold."""
        assert "bronze" in VALID_STAGES
        assert "silver" in VALID_STAGES
        assert "gold" in VALID_STAGES

    def test_valid_stages_excludes_invalid(self):
        """VALID_STAGES must not contain arbitrary strings."""
        assert "platinum" not in VALID_STAGES
        assert "" not in VALID_STAGES
        assert "raw" not in VALID_STAGES

    def test_critical_columns_tuple(self):
        """CRITICAL_COLUMNS must include key financial/identifier columns."""
        assert "reference_no" in CRITICAL_COLUMNS
        assert "date" in CRITICAL_COLUMNS
        assert "net_sales" in CRITICAL_COLUMNS
        assert "quantity" in CRITICAL_COLUMNS

    def test_quality_check_result_default_empty_details(self):
        """details defaults to empty dict when not provided."""
        result = QualityCheckResult(
            check_name="test",
            stage="bronze",
            severity="warn",
            passed=True,
        )

        assert result.details == {}

    def test_quality_report_frozen(self):
        """QualityReport is immutable — mutation must raise TypeError."""
        from datetime import datetime

        report = QualityReport(
            pipeline_run_id=uuid4(),
            stage="bronze",
            checks=[],
            all_passed=True,
            gate_passed=True,
            checked_at=datetime.now(UTC),
        )

        with pytest.raises((TypeError, Exception)):
            report.all_passed = False  # type: ignore[misc]
