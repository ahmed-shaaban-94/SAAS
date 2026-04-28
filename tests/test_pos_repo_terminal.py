"""Unit tests for PosRepository — terminal session CRUD."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _make_execute(rows, *, mode: str = "one"):
    mapping_mock = MagicMock()
    if mode == "one":
        mapping_mock.one.return_value = rows
    elif mode == "first":
        mapping_mock.first.return_value = rows
    elif mode == "all":
        mapping_mock.all.return_value = rows
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    return chain


class TestCreateTerminalSession:
    def test_returns_row_dict(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "tenant_id": 10,
            "site_code": "S1",
            "staff_id": "USR1",
            "terminal_name": "Terminal-1",
            "status": "open",
            "opened_at": datetime.datetime(2026, 4, 15, 8, 0),
            "closed_at": None,
            "opening_cash": Decimal("200.00"),
            "closing_cash": None,
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.create_terminal_session(
            tenant_id=10, site_code="S1", staff_id="USR1", opening_cash=Decimal("200.00")
        )
        assert result["id"] == 1
        assert result["status"] == "open"
        mock_session.execute.assert_called_once()

    def test_sql_contains_insert(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(
            {
                "id": 1,
                "tenant_id": 1,
                "site_code": "S1",
                "staff_id": "U",
                "terminal_name": "T",
                "status": "open",
                "opened_at": datetime.datetime(2026, 1, 1),
                "closed_at": None,
                "opening_cash": Decimal("0"),
                "closing_cash": None,
            },
            mode="one",
        )
        repo.create_terminal_session(tenant_id=1, site_code="S1", staff_id="U")
        sql_text = str(mock_session.execute.call_args[0][0])
        assert "INSERT INTO pos.terminal_sessions" in sql_text
        assert "RETURNING" in sql_text

    def test_params_passed_correctly(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(
            {
                "id": 2,
                "tenant_id": 5,
                "site_code": "PHX",
                "staff_id": "DR1",
                "terminal_name": "Desk-2",
                "status": "open",
                "opened_at": datetime.datetime(2026, 4, 15),
                "closed_at": None,
                "opening_cash": Decimal("500"),
                "closing_cash": None,
            },
            mode="one",
        )
        repo.create_terminal_session(
            tenant_id=5,
            site_code="PHX",
            staff_id="DR1",
            terminal_name="Desk-2",
            opening_cash=Decimal("500"),
        )
        params = mock_session.execute.call_args[0][1]
        assert params["tenant_id"] == 5
        assert params["site_code"] == "PHX"
        assert params["terminal_name"] == "Desk-2"
        assert params["opening_cash"] == Decimal("500")


class TestUpdateTerminalStatus:
    def test_returns_updated_row(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "tenant_id": 1,
            "site_code": "S1",
            "staff_id": "U",
            "terminal_name": "T",
            "status": "closed",
            "opened_at": datetime.datetime(2026, 4, 15, 8, 0),
            "closed_at": datetime.datetime(2026, 4, 15, 18, 0),
            "opening_cash": Decimal("200"),
            "closing_cash": Decimal("300"),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="first")
        result = repo.update_terminal_status(
            1, status="closed", tenant_id=1, closing_cash=Decimal("300")
        )
        assert result["status"] == "closed"
        assert result["closing_cash"] == Decimal("300")

    def test_returns_none_when_not_found(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.update_terminal_status(999, status="closed", tenant_id=1) is None

    def test_sql_uses_coalesce_for_closing_cash(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.update_terminal_status(1, status="active", tenant_id=1)
        sql_text = str(mock_session.execute.call_args[0][0])
        assert "COALESCE" in sql_text


class TestGetTerminalSession:
    def test_returns_row(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 7,
            "tenant_id": 3,
            "site_code": "X",
            "staff_id": "U",
            "terminal_name": "T",
            "status": "active",
            "opened_at": datetime.datetime(2026, 4, 15),
            "closed_at": None,
            "opening_cash": Decimal("0"),
            "closing_cash": None,
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_terminal_session(7, tenant_id=3)
        assert result["id"] == 7

    def test_returns_none_when_missing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_terminal_session(9999, tenant_id=1) is None


class TestGetActiveTerminals:
    def test_returns_list(self, repo: PosRepository, mock_session: MagicMock):
        rows = [
            {
                "id": 1,
                "tenant_id": 1,
                "site_code": "S1",
                "staff_id": "U",
                "terminal_name": "T1",
                "status": "active",
                "opened_at": datetime.datetime(2026, 4, 15),
                "closed_at": None,
                "opening_cash": Decimal("0"),
                "closing_cash": None,
            },
        ]
        mock_session.execute.return_value = _make_execute(rows, mode="all")
        result = repo.get_active_terminals(tenant_id=1)
        assert len(result) == 1
        assert result[0]["status"] == "active"

    def test_sql_excludes_closed(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.get_active_terminals(tenant_id=1)
        sql = str(mock_session.execute.call_args[0][0])
        assert "status" in sql
        assert "closed" in sql
