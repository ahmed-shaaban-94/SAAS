"""Tests for Phase 3 — credentials.py (store_credential / load_credential).

All pgcrypto SQL is mocked — no live database required.
Tests cover:
  - store_credential: happy path (insert + upsert via ON CONFLICT)
  - load_credential: found / not found
  - Missing CONTROL_CENTER_CREDS_KEY raises ValueError immediately
  - Plain value is never present in any log call
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session(fetchone_return=None):
    """Build a mock SQLAlchemy session that returns fetchone_return."""
    session = MagicMock()
    execute_result = MagicMock()
    execute_result.fetchone.return_value = fetchone_return
    session.execute.return_value = execute_result
    return session


# ---------------------------------------------------------------------------
# store_credential tests
# ---------------------------------------------------------------------------


class TestStoreCredential:
    def test_returns_row_id_on_success(self):
        """store_credential returns the integer id from RETURNING id."""
        from datapulse.control_center.credentials import store_credential

        row = MagicMock()
        row.__getitem__ = lambda self, idx: 42  # row[0] == 42
        session = _mock_session(fetchone_return=row)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "test-secret-key"
            result = store_credential(
                session,
                connection_id=7,
                tenant_id=1,
                cred_type="password",
                plain_value="supersecret",
            )

        assert result == 42

    def test_execute_called_once_with_parameterized_query(self):
        """Verifies that execute() is called exactly once and uses parameters."""
        from datapulse.control_center.credentials import store_credential

        row = MagicMock()
        row.__getitem__ = lambda self, idx: 99
        session = _mock_session(fetchone_return=row)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "k"
            store_credential(
                session,
                connection_id=3,
                tenant_id=2,
                cred_type="password",
                plain_value="pw",
            )

        assert session.execute.call_count == 1
        # Verify params dict was passed as second arg
        params = session.execute.call_args[0][1]
        assert params["connection_id"] == 3
        assert params["tenant_id"] == 2
        assert params["cred_type"] == "password"
        assert params["plain_value"] == "pw"
        assert params["key"] == "k"

    def test_raises_runtime_error_when_returning_returns_none(self):
        """store_credential raises RuntimeError when INSERT returns no row."""
        from datapulse.control_center.credentials import store_credential

        session = _mock_session(fetchone_return=None)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "k"
            with pytest.raises(RuntimeError, match="INSERT RETURNING returned no row"):
                store_credential(
                    session,
                    connection_id=1,
                    tenant_id=1,
                    cred_type="password",
                    plain_value="pw",
                )

    def test_raises_value_error_when_key_empty(self):
        """store_credential raises ValueError when creds key is not set."""
        from datapulse.control_center.credentials import store_credential

        session = MagicMock()

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = ""
            with pytest.raises(ValueError, match="CONTROL_CENTER_CREDS_KEY"):
                store_credential(
                    session,
                    connection_id=1,
                    tenant_id=1,
                    cred_type="password",
                    plain_value="pw",
                )

        # DB must NOT be touched when key is empty
        session.execute.assert_not_called()

    def test_plain_value_not_in_log(self, caplog):
        """Verify the plain_value is never emitted in structured log output."""
        import logging  # noqa: PLC0415

        from datapulse.control_center.credentials import store_credential  # noqa: PLC0415

        row = MagicMock()
        row.__getitem__ = lambda self, idx: 1
        session = _mock_session(fetchone_return=row)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "k"
            with caplog.at_level(logging.DEBUG):
                store_credential(
                    session,
                    connection_id=1,
                    tenant_id=1,
                    cred_type="password",
                    plain_value="TOP_SECRET_PLAIN_VALUE",
                )

        for record in caplog.records:
            assert "TOP_SECRET_PLAIN_VALUE" not in record.getMessage()
            assert "TOP_SECRET_PLAIN_VALUE" not in str(record.__dict__)


# ---------------------------------------------------------------------------
# load_credential tests
# ---------------------------------------------------------------------------


class TestLoadCredential:
    def test_returns_decrypted_value_when_found(self):
        """load_credential returns the decrypted string from the DB row."""
        from datapulse.control_center.credentials import load_credential

        row = MagicMock()
        row.__getitem__ = lambda self, idx: "decrypted-password"
        session = _mock_session(fetchone_return=row)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "k"
            result = load_credential(session, connection_id=5, tenant_id=1)

        assert result == "decrypted-password"

    def test_returns_none_when_not_found(self):
        """load_credential returns None when no credential row exists."""
        from datapulse.control_center.credentials import load_credential

        session = _mock_session(fetchone_return=None)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "k"
            result = load_credential(session, connection_id=99, tenant_id=1)

        assert result is None

    def test_raises_value_error_when_key_empty(self):
        """load_credential raises ValueError immediately when key is empty."""
        from datapulse.control_center.credentials import load_credential

        session = MagicMock()

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = ""
            with pytest.raises(ValueError, match="CONTROL_CENTER_CREDS_KEY"):
                load_credential(session, connection_id=1, tenant_id=1)

        session.execute.assert_not_called()

    def test_parameterized_query_uses_correct_args(self):
        """load_credential passes correct params to session.execute()."""
        from datapulse.control_center.credentials import load_credential

        row = MagicMock()
        row.__getitem__ = lambda self, idx: "pw"
        session = _mock_session(fetchone_return=row)

        with patch("datapulse.control_center.credentials.get_settings") as mock_settings:
            mock_settings.return_value.control_center_creds_key = "mykey"
            load_credential(session, connection_id=7, tenant_id=3, cred_type="service_account")

        params = session.execute.call_args[0][1]
        assert params["connection_id"] == 7
        assert params["tenant_id"] == 3
        assert params["cred_type"] == "service_account"
        assert params["key"] == "mykey"
