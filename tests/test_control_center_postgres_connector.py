"""Tests for Phase 3 — PostgresConnector.

psycopg2 is mocked throughout — no live database required.
Tests cover:
  - test(): happy path, missing fields, connection failure, missing password
  - preview(): happy path, identifier validation (SQL injection prevention)
  - _validate_identifier: allowlist enforcement
  - Password loading via _load_password (session path + test-only _password path)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_connector(session=None, connection_id=5, tenant_id=1):
    from datapulse.control_center.connectors.postgres import PostgresConnector

    return PostgresConnector(session=session, connection_id=connection_id, tenant_id=tenant_id)


def _basic_config(**overrides) -> dict:
    cfg = {
        "host": "db.example.com",
        "port": 5432,
        "database": "sales",
        "user": "reader",
        "schema": "public",
        "table": "orders",
        "_password": "testpw",  # test-only escape hatch
    }
    cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# test() method
# ---------------------------------------------------------------------------


class TestPostgresConnectorTest:
    def test_ok_when_select_1_succeeds(self):
        """test() returns ok=True when psycopg2.connect + SELECT 1 succeeds."""
        connector = _make_connector()
        config = _basic_config()

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            result = connector.test(tenant_id=1, config=config)

        assert result.ok is True
        assert result.latency_ms is not None
        assert result.error is None

    def test_returns_error_on_connection_failure(self):
        """test() returns ok=False when psycopg2.connect raises."""
        connector = _make_connector()
        config = _basic_config()

        with patch("psycopg2.connect", side_effect=Exception("timeout")):
            result = connector.test(tenant_id=1, config=config)

        assert result.ok is False
        assert "timeout" in (result.error or "")

    def test_returns_error_when_host_missing(self):
        """test() returns error when required config fields are absent."""
        connector = _make_connector()
        config = _basic_config(host="")

        result = connector.test(tenant_id=1, config=config)

        assert result.ok is False
        assert "config_missing" in (result.error or "")

    def test_returns_error_when_password_not_available(self):
        """test() returns ok=False when no credential is stored and no _password."""
        connector = _make_connector(session=MagicMock())
        config = _basic_config()
        # Remove test-only _password key
        del config["_password"]

        with (
            patch(
                "datapulse.control_center.credentials.load_credential",
                return_value=None,
            ),
            patch("datapulse.control_center.credentials.get_settings") as ms,
        ):
            ms.return_value.control_center_creds_key = "k"
            result = connector.test(tenant_id=1, config=config)

        assert result.ok is False
        assert "credential" in (result.error or "").lower()

    def test_returns_error_when_key_not_set(self):
        """test() returns ok=False when CONTROL_CENTER_CREDS_KEY is empty."""
        session = MagicMock()
        connector = _make_connector(session=session)
        config = _basic_config()
        del config["_password"]

        with patch(
            "datapulse.control_center.credentials.get_settings",
        ) as ms:
            ms.return_value.control_center_creds_key = ""
            result = connector.test(tenant_id=1, config=config)

        assert result.ok is False
        assert "CONTROL_CENTER_CREDS_KEY" in (result.error or "")

    def test_psycopg2_import_error_returns_graceful_error(self):
        """test() returns ok=False with a clear message when psycopg2 is absent."""
        connector = _make_connector()
        config = _basic_config()

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psycopg2":
                raise ImportError("No module named 'psycopg2'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = connector.test(tenant_id=1, config=config)

        assert result.ok is False
        assert "psycopg2" in (result.error or "")


# ---------------------------------------------------------------------------
# preview() method
# ---------------------------------------------------------------------------


class TestPostgresConnectorPreview:
    def _make_mock_psycopg2(self, rows: list[dict]):
        """Return a patched psycopg2 module with rows as cursor result."""
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = rows
        mock_cur.description = [
            (col, None, None, None, None, None, None) for col in (rows[0].keys() if rows else [])
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        return mock_conn

    def test_returns_preview_result_with_columns(self):
        """preview() returns ConnectionPreviewResult with correct column count."""
        connector = _make_connector()
        config = _basic_config()

        rows = [
            {"id": 1, "amount": 100.0, "name": "Alice"},
            {"id": 2, "amount": 200.0, "name": "Bob"},
        ]
        mock_conn = self._make_mock_psycopg2(rows)

        with (
            patch("psycopg2.connect", return_value=mock_conn),
            patch("psycopg2.extras.RealDictCursor", MagicMock()),
        ):
            # Patch cursor to return real dicts
            mock_conn.cursor.return_value.__enter__ = lambda s: s
            mock_conn.cursor.return_value.fetchall.return_value = rows
            mock_conn.cursor.return_value.description = [("id",), ("amount",), ("name",)]

            result = connector.preview(tenant_id=1, config=config)

        assert result.row_count_estimate == 2
        assert len(result.columns) == 3

    def test_raises_on_invalid_schema_identifier(self):
        """preview() raises ValueError when schema contains invalid characters."""
        from datapulse.control_center.connectors.postgres import _validate_identifier

        with pytest.raises(ValueError, match="schema"):
            _validate_identifier("public; DROP TABLE users--", "schema")

    def test_raises_on_invalid_table_identifier(self):
        """preview() raises ValueError when table name contains SQL injection."""
        from datapulse.control_center.connectors.postgres import _validate_identifier

        with pytest.raises(ValueError, match="table"):
            _validate_identifier("orders' OR '1'='1", "table")

    def test_valid_identifier_accepted(self):
        """_validate_identifier accepts normal alphanumeric identifiers."""
        from datapulse.control_center.connectors.postgres import _validate_identifier

        assert _validate_identifier("orders_2024", "table") == "orders_2024"
        assert _validate_identifier("schema_name", "schema") == "schema_name"
        assert _validate_identifier("Table$1", "table") == "Table$1"

    def test_raises_when_config_missing_table(self):
        """preview() raises ValueError when 'table' is missing from config."""
        connector = _make_connector()
        config = _basic_config(table="")

        with pytest.raises(ValueError, match="config_missing"):
            connector.preview(tenant_id=1, config=config)

    def test_raises_on_psycopg2_error(self):
        """preview() raises ValueError wrapping psycopg2 exception."""
        connector = _make_connector()
        config = _basic_config()

        with (
            patch("psycopg2.connect", side_effect=Exception("auth failed")),
            pytest.raises(ValueError, match="preview_failed"),
        ):
            connector.preview(tenant_id=1, config=config)

    def test_raises_when_password_not_available(self):
        """preview() raises ValueError when no password is stored."""
        connector = _make_connector(session=MagicMock())
        config = _basic_config()
        del config["_password"]

        with (
            patch(
                "datapulse.control_center.credentials.load_credential",
                return_value=None,
            ),
            patch("datapulse.control_center.credentials.get_settings") as ms,
            pytest.raises(ValueError, match="credential"),
        ):
            ms.return_value.control_center_creds_key = "k"
            connector.preview(tenant_id=1, config=config)


# ---------------------------------------------------------------------------
# _load_password tests
# ---------------------------------------------------------------------------


class TestLoadPassword:
    def test_uses_test_password_when_present(self):
        """_load_password returns config['_password'] without DB call."""
        connector = _make_connector()
        result = connector._load_password(tenant_id=1, config={"_password": "mypw"})
        assert result == "mypw"

    def test_raises_when_no_session_and_no_test_password(self):
        """_load_password raises ValueError when session is None and no _password."""
        connector = _make_connector(session=None)
        with pytest.raises(ValueError, match="no session"):
            connector._load_password(tenant_id=1, config={})

    def test_raises_when_credential_not_stored(self):
        """_load_password raises ValueError when load_credential returns None."""
        session = MagicMock()
        connector = _make_connector(session=session)

        with (
            patch(
                "datapulse.control_center.credentials.load_credential",
                return_value=None,
            ),
            patch("datapulse.control_center.credentials.get_settings") as ms,
            pytest.raises(ValueError, match="no stored credential"),
        ):
            ms.return_value.control_center_creds_key = "k"
            connector._load_password(tenant_id=1, config={})
