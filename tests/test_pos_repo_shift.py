"""Unit tests for PosRepository — shift records and cash drawer events."""

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


class TestCreateShiftRecord:
    def test_creates_open_shift(self, repo: PosRepository, mock_session: MagicMock):
        opened = datetime.datetime(2026, 4, 15, 8, 0)
        expected = {
            "id": 1,
            "terminal_id": 5,
            "tenant_id": 1,
            "staff_id": "USR",
            "shift_date": datetime.date(2026, 4, 15),
            "opened_at": opened,
            "closed_at": None,
            "opening_cash": Decimal("200"),
            "closing_cash": None,
            "expected_cash": None,
            "variance": None,
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.create_shift_record(
            terminal_id=5,
            tenant_id=1,
            staff_id="USR",
            shift_date=datetime.date(2026, 4, 15),
            opened_at=opened,
            opening_cash=Decimal("200"),
        )
        assert result["closed_at"] is None
        assert result["opening_cash"] == Decimal("200")


class TestGetCurrentShift:
    def test_returns_open_shift(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 3,
            "terminal_id": 5,
            "tenant_id": 1,
            "staff_id": "USR",
            "shift_date": datetime.date(2026, 4, 15),
            "opened_at": datetime.datetime(2026, 4, 15, 8, 0),
            "closed_at": None,
            "opening_cash": Decimal("200"),
            "closing_cash": None,
            "expected_cash": None,
            "variance": None,
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_current_shift(5, tenant_id=1)
        assert result["id"] == 3

    def test_sql_filters_closed_at_null(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.get_current_shift(5, tenant_id=1)
        sql = str(mock_session.execute.call_args[0][0])
        assert "closed_at" in sql
        assert "IS NULL" in sql


class TestUpdateShiftRecord:
    def test_closes_shift_with_variance(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 3,
            "terminal_id": 5,
            "tenant_id": 1,
            "staff_id": "USR",
            "shift_date": datetime.date(2026, 4, 15),
            "opened_at": datetime.datetime(2026, 4, 15, 8, 0),
            "closed_at": datetime.datetime(2026, 4, 15, 18, 0),
            "opening_cash": Decimal("200"),
            "closing_cash": Decimal("850"),
            "expected_cash": Decimal("840"),
            "variance": Decimal("10"),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="first")
        result = repo.update_shift_record(
            3,
            tenant_id=1,
            closing_cash=Decimal("850"),
            expected_cash=Decimal("840"),
            variance=Decimal("10"),
            closed_at=datetime.datetime(2026, 4, 15, 18, 0),
        )
        assert result["variance"] == Decimal("10")


class TestRecordCashEvent:
    def test_records_sale_event(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "terminal_id": 5,
            "tenant_id": 1,
            "event_type": "sale",
            "amount": Decimal("55.50"),
            "reference_id": "TXN-100",
            "timestamp": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.record_cash_event(
            terminal_id=5,
            tenant_id=1,
            event_type="sale",
            amount=Decimal("55.50"),
            reference_id="TXN-100",
        )
        assert result["event_type"] == "sale"
        assert result["amount"] == Decimal("55.50")

    def test_sql_insert_into_cash_drawer_events(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(
            {
                "id": 1,
                "terminal_id": 1,
                "tenant_id": 1,
                "event_type": "float",
                "amount": Decimal("100"),
                "reference_id": None,
                "timestamp": datetime.datetime(2026, 1, 1),
            },
            mode="one",
        )
        repo.record_cash_event(
            terminal_id=1, tenant_id=1, event_type="float", amount=Decimal("100")
        )
        sql = str(mock_session.execute.call_args[0][0])
        assert "INSERT INTO pos.cash_drawer_events" in sql


class TestGetCashEvents:
    def test_returns_events(self, repo: PosRepository, mock_session: MagicMock):
        rows = [
            {
                "id": 1,
                "terminal_id": 5,
                "tenant_id": 1,
                "event_type": "sale",
                "amount": Decimal("50"),
                "reference_id": None,
                "timestamp": datetime.datetime(2026, 4, 15),
            },
        ]
        mock_session.execute.return_value = _make_execute(rows, mode="all")
        result = repo.get_cash_events(terminal_id=5, tenant_id=1)
        assert len(result) == 1
