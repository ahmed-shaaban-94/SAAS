"""Configurable quality check engine.

Executes quality checks using tenant-configurable rules instead of
hard-coded thresholds. Falls back to sensible defaults when no
custom rules are defined.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.pipeline.quality import QualityCheckResult, QualityReport

log = get_logger(__name__)

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Default rules per stage (used when no custom rules exist for a tenant).
DEFAULT_RULES: dict[str, list[dict[str, Any]]] = {
    "bronze": [
        {
            "check_name": "row_count",
            "severity": "error",
            "config": {"min_rows": 1},
        },
        {
            "check_name": "null_rate",
            "severity": "error",
            "config": {
                "threshold": 5.0,
                "columns": ["reference_no", "date", "net_sales", "quantity"],
            },
        },
        {
            "check_name": "freshness",
            "severity": "warn",
            "config": {"max_age_hours": 48, "date_column": "date"},
        },
    ],
    "silver": [
        {
            "check_name": "null_rate",
            "severity": "error",
            "config": {
                "threshold": 5.0,
                "columns": ["reference_no", "date", "sales", "quantity"],
            },
        },
        {
            "check_name": "row_count",
            "severity": "error",
            "config": {"min_rows": 1},
        },
    ],
    "gold": [
        {
            "check_name": "row_count",
            "severity": "error",
            "config": {"min_rows": 1},
        },
    ],
}

# Trusted stage → (schema, table) mapping — never user-derived
_STAGE_TABLE: dict[str, tuple[str, str]] = {
    "bronze": ("bronze", "sales"),
    "silver": ("public_staging", "stg_sales"),
    "gold": ("public_marts", "fct_sales"),
}

# Allowed column names for dynamic SQL in quality checks
_ALLOWED_COLUMNS = frozenset(
    {
        "reference_no",
        "date",
        "net_sales",
        "sales",
        "quantity",
        "gross_sales",
        "material",
        "customer",
        "site",
        "personel_number",
        "billing_type",
        "material_desc",
        "customer_name",
        "brand",
        "category",
    }
)


def _check_row_count(
    session: Session,
    stage: str,
    config: dict[str, Any],
) -> QualityCheckResult:
    """Check that a table has at least min_rows rows."""
    if stage not in _STAGE_TABLE:
        return QualityCheckResult(
            check_name="row_count",
            stage=stage,
            severity="error",
            passed=False,
            message=f"Unknown stage: {stage}",
        )

    schema, table = _STAGE_TABLE[stage]
    min_rows = config.get("min_rows", 1)

    stmt = text(f"SELECT COUNT(*) FROM {schema}.{table}")
    row_count: int = session.execute(stmt).scalar_one()

    passed = row_count >= min_rows
    return QualityCheckResult(
        check_name="row_count",
        stage=stage,
        severity="error",
        passed=passed,
        message=None if passed else f"{schema}.{table} has {row_count} rows (minimum: {min_rows})",
        details={"row_count": row_count, "min_rows": min_rows},
    )


def _check_null_rate(
    session: Session,
    stage: str,
    config: dict[str, Any],
) -> QualityCheckResult:
    """Check null rate for specified columns against a configurable threshold."""
    if stage not in _STAGE_TABLE:
        return QualityCheckResult(
            check_name="null_rate",
            stage=stage,
            severity="error",
            passed=False,
            message=f"Unknown stage: {stage}",
        )

    schema, table = _STAGE_TABLE[stage]
    threshold = config.get("threshold", 5.0)
    columns = config.get("columns", ["reference_no", "date", "net_sales", "quantity"])

    # Validate column names
    safe_columns = [c for c in columns if c in _ALLOWED_COLUMNS and _SAFE_IDENTIFIER_RE.match(c)]
    if not safe_columns:
        return QualityCheckResult(
            check_name="null_rate",
            stage=stage,
            severity="error",
            passed=True,
            message="No valid columns to check",
        )

    null_exprs = ", ".join(
        f"(COUNT(*) FILTER (WHERE {col} IS NULL)) * 100.0 / NULLIF(COUNT(*), 0) AS {col}_null_pct"
        for col in safe_columns
    )
    stmt = text(f"SELECT {null_exprs} FROM {schema}.{table}")
    row = session.execute(stmt).fetchone()

    null_pcts: dict[str, float] = {}
    for i, col in enumerate(safe_columns):
        null_pcts[col] = round(float(row[i] or 0.0) if row else 0.0, 4)

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
            else f"High null rate in: {list(failing.keys())} (threshold {threshold}%)"
        ),
        details={"columns": null_pcts, "threshold": threshold},
    )


def _check_freshness(
    session: Session,
    stage: str,
    config: dict[str, Any],
) -> QualityCheckResult:
    """Check that the most recent data is within max_age_hours."""
    if stage not in _STAGE_TABLE:
        return QualityCheckResult(
            check_name="freshness",
            stage=stage,
            severity="warn",
            passed=False,
            message=f"Unknown stage: {stage}",
        )

    schema, table = _STAGE_TABLE[stage]
    max_age_hours = config.get("max_age_hours", 48)
    date_column = config.get("date_column", "date")

    if date_column not in _ALLOWED_COLUMNS or not _SAFE_IDENTIFIER_RE.match(date_column):
        return QualityCheckResult(
            check_name="freshness",
            stage=stage,
            severity="warn",
            passed=False,
            message=f"Invalid date column: {date_column}",
        )

    stmt = text(f"SELECT MAX({date_column}) FROM {schema}.{table}")
    max_date = session.execute(stmt).scalar_one()

    if max_date is None:
        return QualityCheckResult(
            check_name="freshness",
            stage=stage,
            severity="warn",
            passed=False,
            message="No data found for freshness check",
            details={"max_date": None, "max_age_hours": max_age_hours},
        )

    if hasattr(max_date, "tzinfo") and max_date.tzinfo is None:
        max_date = max_date.replace(tzinfo=UTC)
    elif not hasattr(max_date, "tzinfo"):
        # It's a date, not datetime
        max_date = datetime(max_date.year, max_date.month, max_date.day, tzinfo=UTC)

    age_hours = (datetime.now(UTC) - max_date).total_seconds() / 3600
    passed = age_hours <= max_age_hours

    return QualityCheckResult(
        check_name="freshness",
        stage=stage,
        severity="warn",
        passed=passed,
        message=(None if passed else f"Data is {age_hours:.1f} hours old (max: {max_age_hours}h)"),
        details={
            "max_date": str(max_date),
            "age_hours": round(age_hours, 1),
            "max_age_hours": max_age_hours,
        },
    )


_CUSTOM_SQL_TIMEOUT_MS = 30_000  # 30 seconds max for custom quality checks


def _check_custom_sql(
    session: Session,
    stage: str,
    config: dict[str, Any],
) -> QualityCheckResult:
    """Run a custom SQL query and check the result against expected value.

    The query must return a single scalar value. Passes if result equals expected.
    Only SELECT queries are allowed (no DDL/DML).
    A statement timeout prevents slow queries from blocking the pipeline.
    """
    query = config.get("query", "")
    expected = config.get("expected", "0")
    timeout_ms = config.get("timeout_ms", _CUSTOM_SQL_TIMEOUT_MS)

    # Safety: only allow SELECT statements
    normalized = query.strip().upper()
    if not normalized.startswith("SELECT"):
        return QualityCheckResult(
            check_name="custom_sql",
            stage=stage,
            severity="warn",
            passed=False,
            message="Custom SQL must be a SELECT statement",
        )

    try:
        # Set a per-statement timeout to prevent slow queries from hanging
        session.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result = session.execute(text(query)).scalar_one()
        actual = str(result)
        passed = actual == str(expected)
        return QualityCheckResult(
            check_name="custom_sql",
            stage=stage,
            severity="warn",
            passed=passed,
            message=None if passed else f"Expected {expected}, got {actual}",
            details={"query": query[:200], "expected": str(expected), "actual": actual},
        )
    except Exception as exc:
        error_msg = str(exc)[:100]
        if "canceling statement due to statement timeout" in str(exc):
            error_msg = f"Custom SQL timed out after {timeout_ms}ms"
        return QualityCheckResult(
            check_name="custom_sql",
            stage=stage,
            severity="warn",
            passed=False,
            message=f"Custom SQL failed: {error_msg}",
            details={"query": query[:200], "error": str(exc)[:200]},
        )


# Registry of check functions
CHECK_REGISTRY: dict[str, Any] = {
    "row_count": _check_row_count,
    "null_rate": _check_null_rate,
    "freshness": _check_freshness,
    "custom_sql": _check_custom_sql,
}


def run_configurable_checks(
    session: Session,
    run_id: UUID,
    stage: str,
    rules: list[dict[str, Any]] | None = None,
) -> QualityReport:
    """Execute quality checks for a stage using provided rules or defaults.

    Args:
        session: SQLAlchemy session.
        run_id: Pipeline run ID.
        stage: Pipeline stage name.
        rules: List of rule dicts with check_name, severity, config.
               Falls back to DEFAULT_RULES if None.

    Returns:
        QualityReport with gate_passed and all check results.
    """
    if rules is None:
        rules = DEFAULT_RULES.get(stage, [])

    results: list[QualityCheckResult] = []

    for rule in rules:
        check_name = rule.get("check_name", "unknown")
        config = rule.get("config", {})
        severity = rule.get("severity", "warn")

        checker = CHECK_REGISTRY.get(check_name)
        if checker is None:
            results.append(
                QualityCheckResult(
                    check_name=check_name,
                    stage=stage,
                    severity=severity,
                    passed=False,
                    message=f"Unknown check: {check_name}",
                )
            )
            continue

        try:
            result = checker(session, stage, config)
            # Override severity from rule definition
            results.append(
                QualityCheckResult(
                    check_name=result.check_name,
                    stage=result.stage,
                    severity=severity,
                    passed=result.passed,
                    message=result.message,
                    details=result.details,
                )
            )
        except Exception as exc:
            log.error(
                "quality_check_error",
                check_name=check_name,
                stage=stage,
                error=str(exc),
            )
            results.append(
                QualityCheckResult(
                    check_name=check_name,
                    stage=stage,
                    severity=severity,
                    passed=False,
                    message=f"Check failed with error: {str(exc)[:100]}",
                )
            )

    all_passed = all(r.passed for r in results) if results else True
    gate_passed = all(r.passed for r in results if r.severity == "error") if results else True

    return QualityReport(
        pipeline_run_id=run_id,
        stage=stage,
        checks=results,
        all_passed=all_passed,
        gate_passed=gate_passed,
        checked_at=datetime.now(UTC),
    )
