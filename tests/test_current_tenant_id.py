"""Integration tests for the canonical ``public.current_tenant_id()`` SQL helper.

Added by migration 098 (issue #547-3). Tests the four edge cases mandated by
the issue: unset session var, empty-string session var, numeric session var,
non-numeric session var.

These are DB-level tests — they connect to a real Postgres and assert SQL
behavior directly. They piggyback on the same reachability guard as
``test_rls_db_integration.py``.
"""

from __future__ import annotations

import os
import socket

import pytest


def _db_is_reachable() -> bool:
    """True when the configured PostgreSQL host accepts TCP connections."""
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


@pytest.fixture()
def db_conn():
    """Raw psycopg2 connection, per-test for fresh session state."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


@requires_real_db
class TestCurrentTenantIdFunction:
    def test_returns_null_when_session_var_is_unset(self, db_conn):
        """A fresh session with no app.tenant_id set → NULL (fail-closed)."""
        with db_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SELECT public.current_tenant_id()")
            (result,) = cur.fetchone()
        assert result is None

    def test_returns_null_when_session_var_is_empty_string(self, db_conn):
        """``SET LOCAL app.tenant_id = ''`` still returns NULL, not 0."""
        with db_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL app.tenant_id = ''")
            cur.execute("SELECT public.current_tenant_id()")
            (result,) = cur.fetchone()
        assert result is None

    def test_returns_int_when_session_var_is_numeric(self, db_conn):
        """Happy path — coerced to INT."""
        with db_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL app.tenant_id = '42'")
            cur.execute("SELECT public.current_tenant_id()")
            (result,) = cur.fetchone()
        assert result == 42

    def test_raises_on_non_numeric_session_var(self, db_conn):
        """Non-numeric values raise ``22P02`` (invalid_text_representation).

        This is the behavior the issue asks for — refuse to silently fail
        closed on a typo, injection attempt, or misconfiguration that sets
        ``app.tenant_id`` to something like ``"1 OR 1=1"``.
        """
        psycopg2 = pytest.importorskip("psycopg2")
        with db_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL app.tenant_id = 'not-a-number'")
            with pytest.raises(psycopg2.errors.InvalidTextRepresentation):
                cur.execute("SELECT public.current_tenant_id()")
