"""Tests for datapulse.tasks.query_tasks — Celery execute_query task."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from celery.exceptions import SoftTimeLimitExceeded

from datapulse.tasks.query_tasks import _serialise, execute_query


class TestSerialise:
    def test_none(self):
        assert _serialise(None) is None

    def test_decimal(self):
        assert _serialise(Decimal("10.5")) == 10.5

    def test_datetime(self):
        dt = datetime(2025, 1, 15, 10, 30)
        assert _serialise(dt) == dt.isoformat()

    def test_date(self):
        d = date(2025, 1, 15)
        assert _serialise(d) == "2025-01-15"

    def test_int(self):
        assert _serialise(42) == 42

    def test_float(self):
        assert _serialise(3.14) == 3.14

    def test_bool(self):
        assert _serialise(True) is True

    def test_string(self):
        assert _serialise("hello") == "hello"

    def test_other_type_becomes_str(self):
        assert _serialise(object()) is not None  # calls str()


class TestExecuteQuery:
    @patch("datapulse.tasks.query_tasks.get_session_factory")
    def test_successful_query(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        # Mock the result proxy
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name", "amount"]
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    (1, "Item A", Decimal("100.50")),
                    (2, "Item B", Decimal("200.75")),
                ]
            )
        )

        # First call: SET LOCAL tenant, second: statement_timeout, third: actual query
        mock_session.execute.side_effect = [MagicMock(), MagicMock(), mock_result]

        result = execute_query("SELECT id, name, amount FROM sales", tenant_id="1")

        assert result["columns"] == ["id", "name", "amount"]
        assert result["row_count"] == 2
        assert result["truncated"] is False
        assert result["rows"][0] == [1, "Item A", 100.50]
        assert "duration_ms" in result
        mock_session.close.assert_called_once()

    @patch("datapulse.tasks.query_tasks.get_session_factory")
    def test_truncation(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        # Generate more rows than the limit
        rows = [(i, f"item_{i}") for i in range(20)]
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.__iter__ = MagicMock(return_value=iter(rows))

        mock_session.execute.side_effect = [MagicMock(), MagicMock(), mock_result]

        result = execute_query("SELECT * FROM big_table", row_limit=5)

        assert result["row_count"] == 5
        assert result["truncated"] is True

    @patch("datapulse.tasks.query_tasks.get_session_factory")
    def test_query_failure_rollback(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        # SET LOCAL + statement_timeout succeed, query fails
        mock_session.execute.side_effect = [MagicMock(), MagicMock(), RuntimeError("SQL error")]

        with pytest.raises(RuntimeError, match="SQL error"):
            execute_query("SELECT * FROM nonexistent")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("datapulse.tasks.query_tasks.get_session_factory")
    def test_with_params(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        mock_result = MagicMock()
        mock_result.keys.return_value = ["id"]
        mock_result.__iter__ = MagicMock(return_value=iter([(1,)]))

        mock_session.execute.side_effect = [MagicMock(), MagicMock(), mock_result]

        result = execute_query(
            "SELECT id FROM sales WHERE site_key = :sk",
            params={"sk": 1},
            tenant_id="42",
        )

        assert result["row_count"] == 1

    @patch("datapulse.tasks.query_tasks.get_session_factory")
    def test_soft_time_limit_returns_error(self, mock_factory):
        """SoftTimeLimitExceeded returns an error dict instead of raising."""
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        mock_session.execute.side_effect = [
            MagicMock(),  # SET LOCAL tenant
            MagicMock(),  # statement_timeout
            SoftTimeLimitExceeded(),  # query hangs
        ]

        result = execute_query("SELECT * FROM huge_table")

        assert result["row_count"] == 0
        assert result["error"] == "Query timed out after 280 seconds"
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("datapulse.tasks.query_tasks.get_session_factory")
    def test_statement_timeout_is_set(self, mock_factory):
        """Verify statement_timeout is set via SET LOCAL."""
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        mock_result = MagicMock()
        mock_result.keys.return_value = ["id"]
        mock_result.__iter__ = MagicMock(return_value=iter([(1,)]))
        mock_session.execute.side_effect = [MagicMock(), MagicMock(), mock_result]

        execute_query("SELECT 1", tenant_id="1")

        # Second execute call should be statement_timeout
        calls = mock_session.execute.call_args_list
        assert len(calls) == 3
        timeout_sql = str(calls[1][0][0])
        assert "statement_timeout" in timeout_sql
