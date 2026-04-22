"""Financial NUMERIC precision drift detection (#547-1).

The primary financial standard in DataPulse is ``NUMERIC(18,4)``. Any column
whose name matches ``/(price|amount|cost|revenue|total)/`` SHOULD either use
``(18,4)`` or carry a ``#precision-exception`` marker in its ``COMMENT ON
COLUMN`` (seeded by migration 099) so a reviewer can tell intentional-by-
design from accidental drift.

This test scans ``information_schema.columns`` and ``pg_description`` against
a live Postgres and fails loudly if any financial-named NUMERIC column
deviates from ``(18,4)`` without the marker.

Skips cleanly when no DB is reachable (same pattern as
``test_rls_db_integration.py`` and ``test_current_tenant_id.py``).
"""

from __future__ import annotations

import os
import re
import socket

import pytest

_FINANCIAL_NAME_RE = re.compile(r"\b(price|amount|cost|revenue|total)\b", re.IGNORECASE)
_EXPECTED_PRECISION = 18
_EXPECTED_SCALE = 4
_EXCEPTION_MARKER = "#precision-exception"


def _db_is_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration

requires_real_db = pytest.mark.skipif(
    not _db_is_reachable(),
    reason="Real PostgreSQL at localhost:5432 is not reachable — skipping.",
)


@pytest.fixture(scope="module")
def db_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    yield conn
    conn.close()


@requires_real_db
def test_financial_named_numeric_columns_use_expected_precision(db_conn):
    """Fail when a financial-named NUMERIC column deviates from (18,4)
    without an annotated exception in COMMENT ON COLUMN.
    """
    query = """
        SELECT
            c.table_schema,
            c.table_name,
            c.column_name,
            c.numeric_precision,
            c.numeric_scale,
            col_description(
                format('%I.%I', c.table_schema, c.table_name)::regclass,
                c.ordinal_position
            ) AS col_comment
        FROM information_schema.columns c
        WHERE c.data_type = 'numeric'
          AND c.table_schema IN ('public', 'bronze', 'public_marts', 'public_staging')
    """
    with db_conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    violations: list[str] = []
    for schema, table, column, precision, scale, comment in rows:
        if not _FINANCIAL_NAME_RE.search(column):
            continue
        if precision == _EXPECTED_PRECISION and scale == _EXPECTED_SCALE:
            continue
        if comment and _EXCEPTION_MARKER in comment:
            continue
        violations.append(
            f"{schema}.{table}.{column}: NUMERIC({precision},{scale}) — "
            f"expected NUMERIC({_EXPECTED_PRECISION},{_EXPECTED_SCALE}) or a "
            f"'{_EXCEPTION_MARKER}' COMMENT ON COLUMN annotation"
        )

    assert not violations, "Financial NUMERIC precision drift detected (#547-1):\n  " + "\n  ".join(
        violations
    )
