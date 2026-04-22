# tests/test_tenant_locale_currency_migration.py
"""Integration test for migration 100 — tenants.locale + currency (#604 Spec 1)."""

from __future__ import annotations

import os
import socket

import pytest

pytestmark = pytest.mark.integration


def _db_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


requires_db = pytest.mark.skipif(not _db_reachable(), reason="no DB")


@requires_db
class TestMigration100:
    def test_locale_column_exists_with_default(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT column_default, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema='bronze' AND table_name='tenants' AND column_name='locale'
            """)
            default, nullable, max_len = cur.fetchone()
        assert default == "'en-US'::character varying"
        assert nullable == "NO"
        assert max_len == 10

    def test_currency_column_exists_with_default(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT column_default, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema='bronze' AND table_name='tenants' AND column_name='currency'
            """)
            default, nullable, max_len = cur.fetchone()
        assert default == "'USD'::bpchar"
        assert nullable == "NO"
        assert max_len == 3

    def test_existing_tenants_preserved_on_defaults(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM bronze.tenants
                WHERE locale IS NULL OR currency IS NULL
            """)
            (cnt,) = cur.fetchone()
        assert cnt == 0


@pytest.fixture()
def db_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    yield conn
    conn.close()
