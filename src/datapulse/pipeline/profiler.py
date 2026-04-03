"""Data profiling module for table and column statistics.

Generates statistical profiles (null rate, cardinality, min/max, distributions)
for pipeline stage tables. Used by quality dashboards and anomaly detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Trusted stage → (schema, table) mapping
_STAGE_TABLE: dict[str, tuple[str, str]] = {
    "bronze": ("bronze", "sales"),
    "silver": ("public_staging", "stg_sales"),
    "gold": ("public_marts", "fct_sales"),
}

# Numeric types that support statistical aggregations
_NUMERIC_TYPES = {"integer", "bigint", "numeric", "real", "double precision", "smallint"}


@dataclass(frozen=True)
class ColumnProfile:
    """Statistical profile for a single database column."""

    column_name: str
    data_type: str
    total_rows: int
    null_count: int
    null_rate: float
    unique_count: int
    cardinality: float  # unique_count / total_rows
    min_value: str | None = None
    max_value: str | None = None
    mean: float | None = None
    stddev: float | None = None
    most_common: list[tuple[str, int]] = field(default_factory=list)


@dataclass(frozen=True)
class TableProfile:
    """Statistical profile for an entire database table."""

    schema_name: str
    table_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    profiled_at: datetime


def profile_table(session: Session, stage: str) -> TableProfile:
    """Generate a statistical profile for a pipeline stage table.

    Collects per-column: null count, unique count, cardinality, min/max,
    and for numeric columns: mean and stddev.
    """
    if stage not in _STAGE_TABLE:
        raise ValueError(f"Unknown stage for profiling: {stage!r}")

    schema, table = _STAGE_TABLE[stage]
    log.info("profiler_start", schema=schema, table=table)

    # Get row count
    row_count: int = session.execute(text(f"SELECT COUNT(*) FROM {schema}.{table}")).scalar_one()

    # Get column metadata
    col_meta_stmt = text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table
        ORDER BY ordinal_position
    """)
    col_rows = session.execute(col_meta_stmt, {"schema": schema, "table": table}).fetchall()

    columns: list[ColumnProfile] = []
    for col_row in col_rows:
        col_name = col_row._mapping["column_name"]
        data_type = col_row._mapping["data_type"]

        if not _SAFE_IDENTIFIER_RE.match(col_name):
            continue

        # Basic stats for every column
        stats_stmt = text(f"""
            SELECT
                COUNT(*) FILTER (WHERE {col_name} IS NULL) AS null_count,
                COUNT(DISTINCT {col_name}) AS unique_count
            FROM {schema}.{table}
        """)
        stats = session.execute(stats_stmt).fetchone()
        null_count = stats._mapping["null_count"]
        unique_count = stats._mapping["unique_count"]

        null_rate = round(null_count / row_count * 100, 2) if row_count > 0 else 0.0
        cardinality = round(unique_count / row_count, 4) if row_count > 0 else 0.0

        # Numeric-specific stats
        mean_val = None
        stddev_val = None
        min_val = None
        max_val = None

        if data_type in _NUMERIC_TYPES:
            num_stmt = text(f"""
                SELECT
                    MIN({col_name})::text,
                    MAX({col_name})::text,
                    AVG({col_name}::numeric),
                    STDDEV({col_name}::numeric)
                FROM {schema}.{table}
            """)
            num_row = session.execute(num_stmt).fetchone()
            if num_row:
                min_val = num_row[0]
                max_val = num_row[1]
                mean_val = round(float(num_row[2]), 2) if num_row[2] is not None else None
                stddev_val = round(float(num_row[3]), 2) if num_row[3] is not None else None
        else:
            # Non-numeric: just min/max as text
            minmax_stmt = text(f"""
                SELECT MIN({col_name})::text, MAX({col_name})::text
                FROM {schema}.{table}
            """)
            mm_row = session.execute(minmax_stmt).fetchone()
            if mm_row:
                min_val = mm_row[0]
                max_val = mm_row[1]

        # Most common values (top 5)
        mc_stmt = text(f"""
            SELECT {col_name}::text AS val, COUNT(*) AS cnt
            FROM {schema}.{table}
            WHERE {col_name} IS NOT NULL
            GROUP BY {col_name}
            ORDER BY cnt DESC
            LIMIT 5
        """)
        mc_rows = session.execute(mc_stmt).fetchall()
        most_common = [(r._mapping["val"], r._mapping["cnt"]) for r in mc_rows]

        columns.append(
            ColumnProfile(
                column_name=col_name,
                data_type=data_type,
                total_rows=row_count,
                null_count=null_count,
                null_rate=null_rate,
                unique_count=unique_count,
                cardinality=cardinality,
                min_value=min_val,
                max_value=max_val,
                mean=mean_val,
                stddev=stddev_val,
                most_common=most_common,
            )
        )

    profile = TableProfile(
        schema_name=schema,
        table_name=table,
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        profiled_at=datetime.now(UTC),
    )
    log.info("profiler_done", schema=schema, table=table, columns=len(columns))
    return profile
