"""DB-level audit_log immutability tests.

Verifies that the append-only trigger installed by migration 094 blocks
UPDATE and DELETE on ``public.audit_log`` for every role (including the
table owner ``datapulse``), while INSERT continues to work.

Runs against a real PostgreSQL. Skipped when one is not reachable on
localhost:5432 or when ``DB_READER_PASSWORD`` is missing — same skip
pattern as :mod:`test_rls_db_integration`.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse, urlunparse

import pytest

pytestmark = pytest.mark.integration


def _db_is_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


requires_real_db = pytest.mark.skipif(
    not _db_is_reachable() or not os.environ.get("DB_READER_PASSWORD"),
    reason=(
        "Real PostgreSQL at localhost:5432 not reachable, or DB_READER_PASSWORD env var is missing."
    ),
)


def _reader_dsn() -> str:
    """Build a ``datapulse_reader`` DSN from ``DATABASE_URL`` + ``DB_READER_PASSWORD``."""
    owner = urlparse(os.environ["DATABASE_URL"])
    host = owner.hostname or "localhost"
    port = owner.port or 5432
    reader_netloc = f"datapulse_reader:{os.environ['DB_READER_PASSWORD']}@{host}:{port}"
    return urlunparse(owner._replace(netloc=reader_netloc))


@pytest.fixture(scope="module")
def owner_conn():
    """Raw psycopg2 connection as the ``datapulse`` owner role."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture(scope="module")
def reader_conn():
    """Raw psycopg2 connection as the ``datapulse_reader`` read-only role."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(_reader_dsn())
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


def _insert_audit_row(conn) -> int:
    """Insert one audit_log row and return its id. Caller must rollback."""
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SET LOCAL app.tenant_id = '1'")
        cur.execute(
            """
            INSERT INTO public.audit_log
                (tenant_id, action, endpoint, method, response_status)
            VALUES (1, 'test.immutable', '/test', 'GET', 200)
            RETURNING id
            """
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


class TestAuditLogImmutability:
    """Verify that ``public.audit_log`` is append-only at the DB level."""

    @requires_real_db
    def test_insert_still_works(self, owner_conn) -> None:
        """INSERT must continue to succeed — trigger is UPDATE/DELETE only."""
        try:
            new_id = _insert_audit_row(owner_conn)
            assert new_id > 0
        finally:
            owner_conn.rollback()

    @requires_real_db
    def test_update_blocked_for_owner(self, owner_conn) -> None:
        """UPDATE as the ``datapulse`` owner role must raise insufficient_privilege."""
        psycopg2 = pytest.importorskip("psycopg2")
        try:
            new_id = _insert_audit_row(owner_conn)
            with (
                owner_conn.cursor() as cur,
                pytest.raises(psycopg2.errors.InsufficientPrivilege),
            ):
                cur.execute(
                    "UPDATE public.audit_log SET action = 'tampered' WHERE id = %s",
                    (new_id,),
                )
        finally:
            owner_conn.rollback()

    @requires_real_db
    def test_delete_blocked_for_owner(self, owner_conn) -> None:
        """DELETE as the ``datapulse`` owner role must raise insufficient_privilege."""
        psycopg2 = pytest.importorskip("psycopg2")
        try:
            new_id = _insert_audit_row(owner_conn)
            with (
                owner_conn.cursor() as cur,
                pytest.raises(psycopg2.errors.InsufficientPrivilege),
            ):
                cur.execute(
                    "DELETE FROM public.audit_log WHERE id = %s",
                    (new_id,),
                )
        finally:
            owner_conn.rollback()

    @requires_real_db
    def test_trigger_message_names_audit_log_and_operation(self, owner_conn) -> None:
        """Trigger message must name the table and the blocked TG_OP for debuggability."""
        psycopg2 = pytest.importorskip("psycopg2")
        try:
            new_id = _insert_audit_row(owner_conn)
            with owner_conn.cursor() as cur:
                try:
                    cur.execute(
                        "UPDATE public.audit_log SET action = 'x' WHERE id = %s",
                        (new_id,),
                    )
                    pytest.fail("UPDATE should have raised InsufficientPrivilege")
                except psycopg2.errors.InsufficientPrivilege as exc:
                    msg = str(exc).lower()
                    assert "audit_log" in msg
                    assert "append-only" in msg or "update" in msg
        finally:
            owner_conn.rollback()
