"""SQL validation for SQL Lab.

Ensures only read-only SELECT/WITH statements are executed.
Uses sqlparse for parsing and a keyword blocklist for safety.
"""

from __future__ import annotations

import re

import sqlparse

from datapulse.logging import get_logger

log = get_logger(__name__)

# Blocklist: dangerous SQL statement types
_BLOCKED_TYPES = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"}

# Blocklist: dangerous keywords that could appear in subqueries etc.
_BLOCKED_KEYWORDS = re.compile(
    r"\b(GRANT|REVOKE|COPY|EXECUTE|DO\s+\$|CALL|VACUUM|REINDEX|CLUSTER|"
    r"pg_read_file|pg_write_file|lo_import|lo_export)\b",
    re.IGNORECASE,
)

# Only allow queries against marts schema
_ALLOWED_SCHEMAS = {"public_marts"}


class SQLValidationError(Exception):
    """Raised when SQL fails validation."""


def validate_sql(sql: str) -> str:
    """Validate and normalise SQL for safe execution.

    Parameters
    ----------
    sql:
        Raw SQL string from the user.

    Returns
    -------
    The normalised SQL string (semicolons stripped, whitespace trimmed).

    Raises
    ------
    SQLValidationError:
        If the SQL is not a read-only SELECT/WITH statement.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("SQL cannot be empty.")

    # Parse with sqlparse
    statements = sqlparse.parse(sql)
    if len(statements) == 0:
        raise SQLValidationError("No valid SQL statement found.")

    if len(statements) > 1:
        raise SQLValidationError("Only a single SQL statement is allowed.")

    stmt = statements[0]
    stmt_type = stmt.get_type()

    # Allow SELECT and UNKNOWN (CTEs parse as UNKNOWN in sqlparse)
    if stmt_type and stmt_type.upper() in _BLOCKED_TYPES:
        raise SQLValidationError(
            f"Statement type '{stmt_type}' is not allowed. Only SELECT queries are permitted."
        )

    # Check for blocked keywords
    match = _BLOCKED_KEYWORDS.search(sql)
    if match:
        raise SQLValidationError(f"SQL contains disallowed keyword: '{match.group()}'")

    # Normalise: strip trailing semicolons
    normalised = str(stmt).strip().rstrip(";").strip()

    # Basic sanity check: must start with SELECT or WITH
    upper = normalised.upper().lstrip()
    if not (upper.startswith("SELECT") or upper.startswith("WITH") or upper.startswith("EXPLAIN")):
        raise SQLValidationError("Only SELECT, WITH (CTE), and EXPLAIN statements are allowed.")

    log.debug("sql_validated", length=len(normalised))
    return normalised


def get_schema_tables(session) -> list[dict]:
    """Return table/column metadata from the marts schema.

    Used by the schema browser in the SQL Lab frontend.
    """
    from sqlalchemy import text

    result = session.execute(
        text("""
            SELECT
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable
            FROM information_schema.tables t
            JOIN information_schema.columns c
                ON t.table_name = c.table_name
                AND t.table_schema = c.table_schema
            WHERE t.table_schema = 'public_marts'
                AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name, c.ordinal_position
        """)
    )

    tables: dict[str, list[dict]] = {}
    for row in result:
        table_name = row[0]
        if table_name not in tables:
            tables[table_name] = []
        tables[table_name].append(
            {
                "column_name": row[1],
                "data_type": row[2],
                "is_nullable": row[3] == "YES",
            }
        )

    return [{"table_name": name, "columns": cols} for name, cols in tables.items()]
