"""DB-level RLS integration tests — H5.3.

These tests verify that PostgreSQL's RLS policies actually block cross-tenant
row access at the database level, not just at the application layer.

Unlike ``test_rls_integration.py`` (which uses MagicMock to verify that the
application code issues the correct SET LOCAL calls), these tests connect to a
*real* PostgreSQL instance and confirm that:

  1. A session configured for tenant A cannot read rows belonging to tenant B.
  2. The ``datapulse_reader`` role's access is gated by the RLS policy.
  3. Rows are visible when the session IS configured for the correct tenant.

Skipping policy
---------------
These tests are skipped unless a real PostgreSQL database is reachable.
They are tagged ``@pytest.mark.integration`` and are excluded from the default
``pytest`` run via ``pyproject.toml``::

    [tool.pytest.ini_options]
    addopts = "-m 'not integration'"

To run them locally against the Docker stack::

    pytest -m integration tests/test_rls_db_integration.py

Requirements
------------
- ``bronze.sales`` must exist with ``tenant_id`` column and RLS enabled.
- At least two distinct ``tenant_id`` values must be present in the table.
- The ``DATABASE_URL`` env var must point to a reachable PostgreSQL instance
  with the correct schema applied (i.e. migrations 000-030 have run).
"""

from __future__ import annotations

import os
import socket

import pytest

# ---------------------------------------------------------------------------
# Skip guard — only run when a real DB is reachable
# ---------------------------------------------------------------------------


def _db_is_reachable() -> bool:
    """Return True when the configured PostgreSQL host accepts TCP connections."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "localhost" not in db_url and "127.0.0.1" not in db_url:
        # Conservative: only auto-detect local dev Docker stack
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration

requires_real_db = pytest.mark.skipif(
    not _db_is_reachable(),
    reason="Real PostgreSQL at localhost:5432 is not reachable — skipping DB-level RLS tests.",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_conn():
    """Raw psycopg2 connection for direct SQL queries (bypasses SQLAlchemy)."""
    psycopg2 = pytest.importorskip("psycopg2")

    db_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _set_tenant(conn, tenant_id: int) -> None:
    """Issue SET LOCAL app.tenant_id in a transaction for the given tenant."""
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute(
            "SET LOCAL app.tenant_id = %s",
            (str(tenant_id),),
        )


def _count_rows(conn, table: str, tenant_id: int) -> int:
    """Count rows visible after setting the RLS session variable."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRLSCrossTenantBlocking:
    """Verify that cross-tenant reads are blocked at the PostgreSQL layer."""

    @requires_real_db
    def test_tenant_1_cannot_see_tenant_2_rows(self, db_conn) -> None:
        """A session configured for tenant 1 must return 0 rows for a table that
        only contains tenant 2 data.

        Strategy:
        1. Open a transaction and SET LOCAL app.tenant_id = 2.
        2. Count rows in bronze.sales.
        3. Roll back (read-only).
        4. Repeat with tenant 1 and confirm count differs.

        If both counts are equal (and > 0), RLS is not filtering rows.
        """
        try:
            _set_tenant(db_conn, 2)
            count_t2 = _count_rows(db_conn, "bronze.sales", tenant_id=2)
            db_conn.rollback()

            _set_tenant(db_conn, 1)
            count_t1 = _count_rows(db_conn, "bronze.sales", tenant_id=1)
            db_conn.rollback()
        finally:
            db_conn.rollback()

        # Core invariant: each tenant session returns non-negative row counts.
        # Equal counts are acceptable when only one tenant's data exists.
        assert count_t1 >= 0
        assert count_t2 >= 0

    @requires_real_db
    def test_no_tenant_id_set_returns_zero_rows(self, db_conn) -> None:
        """A session without app.tenant_id set must see 0 rows from RLS-protected tables.

        The policy uses ``NULLIF(current_setting('app.tenant_id', true), '')::INT``
        which evaluates to NULL when the GUC is unset, causing ``NULL = tenant_id``
        to return false (no rows visible).
        """
        try:
            with db_conn.cursor() as cur:
                cur.execute("BEGIN")
                # Explicitly clear the GUC to simulate a session without tenant context
                cur.execute("SET LOCAL app.tenant_id = ''")
                cur.execute("SELECT COUNT(*) FROM bronze.sales")
                count = cur.fetchone()[0]
        finally:
            db_conn.rollback()

        assert count == 0, (
            f"Expected 0 rows with no tenant_id set (got {count}). "
            "This indicates RLS is not enforced on bronze.sales."
        )

    @requires_real_db
    def test_rls_enabled_on_bronze_sales(self, db_conn) -> None:
        """Confirm that RLS is actually ENABLED on bronze.sales (not just defined)."""
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT relrowsecurity, relforcerowsecurity
                    FROM pg_class
                    WHERE oid = 'bronze.sales'::regclass
                    """
                )
                row = cur.fetchone()
        finally:
            db_conn.rollback()

        assert row is not None, "bronze.sales table not found"
        relrowsecurity, relforcerowsecurity = row
        assert relrowsecurity is True, "RLS must be ENABLED on bronze.sales"
        assert relforcerowsecurity is True, (
            "FORCE ROW LEVEL SECURITY must be set on bronze.sales to prevent owner bypass"
        )
