"""Data quality gate models and check functions.

Quality checks run after each pipeline stage. Checks with severity='error'
block pipeline progression; severity='warn' are non-blocking.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)

VALID_SEVERITIES = frozenset({"warn", "error"})
VALID_STAGES = frozenset({"bronze", "silver", "gold"})

# Critical columns that must have <5% null rate
# Bronze uses net_sales; silver renames it to sales.
# Stage-aware column list built below.
_BRONZE_CRITICAL_COLUMNS = ("reference_no", "date", "net_sales", "quantity")
_SILVER_CRITICAL_COLUMNS = ("reference_no", "date", "sales", "quantity")

# Default (bronze) for backward compatibility
CRITICAL_COLUMNS = _BRONZE_CRITICAL_COLUMNS
_COLUMN_ALLOWLIST = frozenset(_BRONZE_CRITICAL_COLUMNS | frozenset(_SILVER_CRITICAL_COLUMNS))
_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Trusted schema.table mapping — never derived from user input
_STAGE_TABLE: dict[str, tuple[str, str]] = {
    "bronze": ("bronze", "sales"),
    "silver": ("public_staging", "stg_sales"),
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class QualityCheckResult(BaseModel):
    """Output from a single quality check function."""

    model_config = ConfigDict(frozen=True)

    check_name: str
    stage: str
    severity: str  # "error" | "warn"
    passed: bool
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class QualityReport(BaseModel):
    """Aggregated result from all checks for one pipeline stage."""

    model_config = ConfigDict(frozen=True)

    pipeline_run_id: UUID
    stage: str
    checks: list[QualityCheckResult]
    all_passed: bool  # True only when every check passed
    gate_passed: bool  # True when every severity='error' check passed
    checked_at: datetime


class QualityCheckResponse(BaseModel):
    """Single persisted quality check row returned by the API."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    pipeline_run_id: UUID
    check_name: str
    stage: str
    severity: str
    passed: bool
    message: str | None
    details: dict[str, Any]
    checked_at: datetime


class QualityCheckList(BaseModel):
    """Collection of persisted quality checks."""

    model_config = ConfigDict(frozen=True)

    items: list[QualityCheckResponse]
    total: int


class QualityCheckRequest(BaseModel):
    """API request body for running quality checks against a pipeline run."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    stage: str
    tenant_id: int = 1

    @field_validator("stage")
    @classmethod
    def _validate_stage(cls, v: str) -> str:
        if v not in VALID_STAGES:
            raise ValueError(
                f"Invalid stage '{v}'. Must be one of: {', '.join(sorted(VALID_STAGES))}"
            )
        return v


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_row_count(session: Session, run_id: UUID) -> QualityCheckResult:
    """Verify that bronze.sales contains at least one row."""
    stmt = text("SELECT COUNT(*) FROM bronze.sales")
    row_count: int = session.execute(stmt).scalar_one()

    passed = row_count > 0
    return QualityCheckResult(
        check_name="row_count",
        stage="bronze",
        severity="error",
        passed=passed,
        message=None if passed else "bronze.sales is empty — no rows loaded",
        details={"row_count": row_count},
    )


def check_row_delta(session: Session, run_id: UUID) -> QualityCheckResult:
    """Warn when the current load is more than 50% smaller than the previous run."""
    current_stmt = text("SELECT COUNT(*) FROM bronze.sales")
    current: int = session.execute(current_stmt).scalar_one()

    prev_stmt = text("""
        SELECT rows_loaded
        FROM public.pipeline_runs
        WHERE id != :run_id
          AND rows_loaded IS NOT NULL
        ORDER BY started_at DESC
        LIMIT 1
    """)
    prev_row = session.execute(prev_stmt, {"run_id": str(run_id)}).fetchone()

    if prev_row is None or prev_row._mapping["rows_loaded"] is None:
        return QualityCheckResult(
            check_name="row_delta",
            stage="bronze",
            severity="warn",
            passed=True,
            message="No previous run found — skipping delta check",
            details={"current": current, "previous": None, "delta_pct": None},
        )

    previous: int = prev_row._mapping["rows_loaded"]
    if previous == 0:
        return QualityCheckResult(
            check_name="row_delta",
            stage="bronze",
            severity="warn",
            passed=True,
            message="Previous run had zero rows — skipping delta check",
            details={"current": current, "previous": 0, "delta_pct": None},
        )

    delta_pct = round(abs(current - previous) / previous * 100, 2)
    passed = delta_pct <= 50.0
    return QualityCheckResult(
        check_name="row_delta",
        stage="bronze",
        severity="warn",
        passed=passed,
        message=(
            None if passed else f"Row count dropped {delta_pct}% vs previous run (threshold 50%)"
        ),
        details={"current": current, "previous": previous, "delta_pct": delta_pct},
    )


def check_schema_drift(session: Session, run_id: UUID) -> QualityCheckResult:
    """Verify that all expected bronze.sales columns are present in the DB."""
    from datapulse.bronze.column_map import COLUMN_MAP

    expected: set[str] = set(COLUMN_MAP.values())

    stmt = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'sales'
          AND table_schema = 'bronze'
    """)
    rows = session.execute(stmt).fetchall()
    actual: set[str] = {r._mapping["column_name"] for r in rows}

    # Exclude system-managed columns that the loader does not own
    system_cols = {"id", "tenant_id", "loaded_at"}
    actual_data_cols = actual - system_cols

    missing = sorted(expected - actual_data_cols)
    extra = sorted(actual_data_cols - expected)

    passed = len(missing) == 0
    return QualityCheckResult(
        check_name="schema_drift",
        stage="bronze",
        severity="error",
        passed=passed,
        message=(
            None
            if passed
            else f"Schema drift detected — {len(missing)} expected column(s) missing: {missing}"
        ),
        details={"missing": missing, "extra": extra},
    )


def check_null_rate(
    session: Session,
    run_id: UUID,
    stage: str = "bronze",
) -> QualityCheckResult:
    """Verify critical columns have fewer than 5% NULL values."""
    if stage not in _STAGE_TABLE:
        raise ValueError(f"Unknown stage for null rate check: {stage!r}")
    schema, table = _STAGE_TABLE[stage]

    threshold = 5.0

    # Pick the right column list for the stage
    columns = _SILVER_CRITICAL_COLUMNS if stage == "silver" else _BRONZE_CRITICAL_COLUMNS

    # Validate all column names against the allowlist
    for col in columns:
        if col not in _COLUMN_ALLOWLIST or not _SAFE_IDENTIFIER_RE.match(col):
            raise ValueError(f"Unsafe column name: {col!r}")

    # Single query to check all critical columns at once (avoids N full-table scans)
    null_exprs = ", ".join(
        f"(COUNT(*) FILTER (WHERE {col} IS NULL)) * 100.0 / NULLIF(COUNT(*), 0) AS {col}_null_pct"
        for col in columns
    )
    stmt = text(f"SELECT {null_exprs} FROM {schema}.{table}")
    row = session.execute(stmt).fetchone()

    null_pcts: dict[str, float] = {}
    for i, col in enumerate(columns):
        null_pcts[col] = round(float(row[i] or 0.0) if row is not None else 0.0, 4)

    failing = {col: pct for col, pct in null_pcts.items() if pct >= threshold}
    passed = len(failing) == 0
    return QualityCheckResult(
        check_name="null_rate",
        stage=stage,
        severity="error",
        passed=passed,
        message=(
            None
            if passed
            else f"High null rate in column(s): {list(failing.keys())} (threshold {threshold}%)"
        ),
        details={"columns": null_pcts, "threshold": threshold},
    )


def check_dedup_effective(session: Session, run_id: UUID) -> QualityCheckResult:
    """Warn when silver row count exceeds bronze row count (dedup went wrong)."""
    bronze_stmt = text("SELECT COUNT(*) FROM bronze.sales")
    silver_stmt = text("SELECT COUNT(*) FROM public_staging.stg_sales")

    bronze_count: int = session.execute(bronze_stmt).scalar_one()
    silver_count: int = session.execute(silver_stmt).scalar_one()

    passed = silver_count <= bronze_count
    return QualityCheckResult(
        check_name="dedup_effective",
        stage="silver",
        severity="warn",
        passed=passed,
        message=(
            None
            if passed
            else (
                f"Silver row count ({silver_count:,}) exceeds bronze "
                f"({bronze_count:,}) — deduplication may have failed"
            )
        ),
        details={"bronze_count": bronze_count, "silver_count": silver_count},
    )


def check_financial_signs(session: Session, run_id: UUID) -> QualityCheckResult:
    """Warn when sales and quantity have inconsistent signs (>1% of rows)."""
    total_stmt = text("SELECT COUNT(*) FROM public_staging.stg_sales")
    total: int = session.execute(total_stmt).scalar_one()

    inconsistent_stmt = text("""
        SELECT COUNT(*) AS cnt
        FROM public_staging.stg_sales
        WHERE quantity != 0
          AND SIGN(sales::numeric) != SIGN(quantity::numeric)
    """)
    inconsistent: int = session.execute(inconsistent_stmt).scalar_one()

    pct = round(inconsistent / total * 100, 4) if total > 0 else 0.0
    passed = pct < 1.0
    return QualityCheckResult(
        check_name="financial_signs",
        stage="silver",
        severity="warn",
        passed=passed,
        message=(
            None
            if passed
            else (
                f"{inconsistent:,} rows ({pct}%) have mismatched "
                f"sales/quantity signs (threshold 1%)"
            )
        ),
        details={"inconsistent_count": inconsistent, "total": total, "pct": pct},
    )


_ALLOWED_DBT_TEST_SELECTORS: frozenset[str] = frozenset(
    {
        "staging",
        "marts",
        "bronze",
        "tag:staging",
        "tag:marts",
        "tag:bronze",
    }
)


def run_dbt_tests(
    run_id: UUID,
    selector: str,
    settings: Settings,
) -> QualityCheckResult:
    """Run dbt test for the given selector and return a QualityCheckResult."""
    clean = selector.lstrip("+")
    if clean not in _ALLOWED_DBT_TEST_SELECTORS:
        return QualityCheckResult(
            check_name=f"dbt_test_{selector}",
            stage="gold",
            severity="error",
            passed=False,
            message=f"dbt test selector '{selector}' is not in the allowed list",
            details={},
        )

    cmd = [
        "dbt",
        "test",
        "--project-dir",
        settings.dbt_project_dir,
        "--profiles-dir",
        settings.dbt_profiles_dir,
        "--select",
        selector,
    ]
    log.info("quality_dbt_test_start", run_id=str(run_id), selector=selector)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.pipeline_dbt_timeout,
        )
        passed = proc.returncode == 0
        return QualityCheckResult(
            check_name=f"dbt_test_{selector}",
            stage="gold",
            severity="error",
            passed=passed,
            message=(
                None
                if passed
                else f"dbt test --select {selector} failed (exit code {proc.returncode})"
            ),
            details={
                "stdout": proc.stdout[:500],
                "stderr": proc.stderr[:500],
            },
        )
    except subprocess.TimeoutExpired:
        error_msg = f"dbt test --select {selector} timed out after {settings.pipeline_dbt_timeout}s"
        log.error("quality_dbt_test_timeout", run_id=str(run_id), error=error_msg)
        return QualityCheckResult(
            check_name=f"dbt_test_{selector}",
            stage="gold",
            severity="error",
            passed=False,
            message=error_msg,
            details={"stdout": "", "stderr": error_msg},
        )
    except Exception as exc:
        error_msg = str(exc)
        log.error("quality_dbt_test_error", run_id=str(run_id), error=error_msg)
        return QualityCheckResult(
            check_name=f"dbt_test_{selector}",
            stage="gold",
            severity="error",
            passed=False,
            message=error_msg,
            details={"stdout": "", "stderr": error_msg},
        )


# ---------------------------------------------------------------------------
# Stage → check function mapping
# ---------------------------------------------------------------------------

STAGE_CHECKS: dict[str, list[Callable[..., QualityCheckResult]]] = {
    "bronze": [check_row_count, check_row_delta, check_schema_drift, check_null_rate],
    "silver": [check_dedup_effective, check_null_rate, check_financial_signs],
    "gold": [run_dbt_tests],
}
