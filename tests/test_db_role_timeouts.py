"""DB-level role timeout tests.

Verifies that migration 094 sets the expected ``statement_timeout``,
``idle_in_transaction_session_timeout`` and ``lock_timeout`` as role
defaults on ``datapulse`` and ``datapulse_reader``, and that
``SET LOCAL`` inside a transaction still overrides the role default —
which is how :mod:`datapulse.api.deps` keeps its tighter 30s cap.

Runs against a real PostgreSQL. Skipped when one is not reachable.
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
    owner = urlparse(os.environ["DATABASE_URL"])
    host = owner.hostname or "localhost"
    port = owner.port or 5432
    reader_netloc = f"datapulse_reader:{os.environ['DB_READER_PASSWORD']}@{host}:{port}"
    return urlunparse(owner._replace(netloc=reader_netloc))


@pytest.fixture
def owner_conn():
    """Fresh connection per test — role defaults only apply to new sessions."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True  # we only SHOW / SET LOCAL
    yield conn
    conn.close()


@pytest.fixture
def reader_conn():
    """Fresh connection per test as the datapulse_reader role."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(_reader_dsn())
    conn.autocommit = True
    yield conn
    conn.close()


def _show(conn, name: str) -> str:
    with conn.cursor() as cur:
        cur.execute(f"SHOW {name}")
        row = cur.fetchone()
        assert row is not None
        return str(row[0])


class TestReaderRoleTimeouts:
    """Reader role gets tight defaults — API reads should never hold long."""

    @requires_real_db
    def test_reader_statement_timeout_default(self, reader_conn) -> None:
        assert _show(reader_conn, "statement_timeout") == "15s"

    @requires_real_db
    def test_reader_idle_in_transaction_timeout_default(self, reader_conn) -> None:
        assert _show(reader_conn, "idle_in_transaction_session_timeout") == "30s"

    @requires_real_db
    def test_reader_lock_timeout_default(self, reader_conn) -> None:
        assert _show(reader_conn, "lock_timeout") == "5s"


class TestAppRoleTimeouts:
    """App role gets looser defaults to accommodate pipeline + dbt runs."""

    @requires_real_db
    def test_app_statement_timeout_default(self, owner_conn) -> None:
        # Postgres normalises '120s' to '2min' on ALTER ROLE.
        assert _show(owner_conn, "statement_timeout") == "2min"

    @requires_real_db
    def test_app_idle_in_transaction_timeout_default(self, owner_conn) -> None:
        assert _show(owner_conn, "idle_in_transaction_session_timeout") == "5min"

    @requires_real_db
    def test_app_lock_timeout_default(self, owner_conn) -> None:
        assert _show(owner_conn, "lock_timeout") == "10s"


class TestSessionLocalStillWins:
    """Proves deps.py ``SET LOCAL statement_timeout = '30s'`` still overrides."""

    @requires_real_db
    def test_set_local_overrides_role_default(self, owner_conn) -> None:
        with owner_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("SHOW statement_timeout")
            row = cur.fetchone()
            cur.execute("ROLLBACK")
        assert row is not None
        assert str(row[0]) == "5s"
