"""Unit tests for PosRepository — void log, returns, bronze write."""

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


class TestCreateVoidLog:
    def test_creates_void_record(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "transaction_id": 55,
            "tenant_id": 1,
            "voided_by": "SUPERVISOR",
            "reason": "customer request",
            "voided_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.create_void_log(
            transaction_id=55,
            tenant_id=1,
            voided_by="SUPERVISOR",
            reason="customer request",
        )
        assert result["voided_by"] == "SUPERVISOR"
        assert result["transaction_id"] == 55

    def test_sql_appends_void_log(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(
            {
                "id": 1,
                "transaction_id": 1,
                "tenant_id": 1,
                "voided_by": "S",
                "reason": "R",
                "voided_at": datetime.datetime(2026, 1, 1),
            },
            mode="one",
        )
        repo.create_void_log(transaction_id=1, tenant_id=1, voided_by="S", reason="R")
        sql = str(mock_session.execute.call_args[0][0])
        assert "INSERT INTO pos.void_log" in sql


class TestGetVoidLog:
    def test_returns_void_record(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 1,
            "transaction_id": 55,
            "tenant_id": 1,
            "voided_by": "SUPERVISOR",
            "reason": "Test",
            "voided_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_void_log(55, tenant_id=1)
        assert result["id"] == 1

    def test_returns_none_when_not_voided(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_void_log(100, tenant_id=1) is None


class TestCreateReturn:
    def test_creates_return_record(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "tenant_id": 1,
            "original_transaction_id": 55,
            "return_transaction_id": None,
            "staff_id": "USR",
            "reason": "defective",
            "refund_amount": Decimal("50"),
            "refund_method": "cash",
            "notes": None,
            "created_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.create_return(
            tenant_id=1,
            original_transaction_id=55,
            staff_id="USR",
            reason="defective",
            refund_amount=Decimal("50"),
            refund_method="cash",
        )
        assert result["reason"] == "defective"
        assert result["refund_amount"] == Decimal("50")

    def test_links_return_transaction(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 2,
            "tenant_id": 1,
            "original_transaction_id": 55,
            "return_transaction_id": 60,
            "staff_id": "USR",
            "reason": "wrong_drug",
            "refund_amount": Decimal("25"),
            "refund_method": "credit_note",
            "notes": "Wrong dosage",
            "created_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        repo.create_return(
            tenant_id=1,
            original_transaction_id=55,
            staff_id="USR",
            reason="wrong_drug",
            refund_amount=Decimal("25"),
            refund_method="credit_note",
            return_transaction_id=60,
            notes="Wrong dosage",
        )
        params = mock_session.execute.call_args[0][1]
        assert params["return_transaction_id"] == 60
        assert params["notes"] == "Wrong dosage"


class TestGetReturn:
    def test_returns_row(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 1,
            "tenant_id": 1,
            "original_transaction_id": 55,
            "return_transaction_id": None,
            "staff_id": "U",
            "reason": "expired",
            "refund_amount": Decimal("10"),
            "refund_method": "cash",
            "notes": None,
            "created_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        assert repo.get_return(1, tenant_id=1)["reason"] == "expired"

    def test_returns_none_when_missing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_return(9999, tenant_id=1) is None


class TestListReturnsForTransaction:
    def test_returns_all_linked_returns(self, repo: PosRepository, mock_session: MagicMock):
        rows = [
            {
                "id": 1,
                "tenant_id": 1,
                "original_transaction_id": 55,
                "return_transaction_id": None,
                "staff_id": "U",
                "reason": "defective",
                "refund_amount": Decimal("10"),
                "refund_method": "cash",
                "notes": None,
                "created_at": datetime.datetime(2026, 4, 15),
            },
            {
                "id": 2,
                "tenant_id": 1,
                "original_transaction_id": 55,
                "return_transaction_id": None,
                "staff_id": "U",
                "reason": "expired",
                "refund_amount": Decimal("5"),
                "refund_method": "cash",
                "notes": None,
                "created_at": datetime.datetime(2026, 4, 15),
            },
        ]
        mock_session.execute.return_value = _make_execute(rows, mode="all")
        result = repo.list_returns_for_transaction(55, tenant_id=1)
        assert len(result) == 2

    def test_sql_filters_by_original_txn(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.list_returns_for_transaction(55, tenant_id=1)
        params = mock_session.execute.call_args[0][1]
        assert params["original_txn_id"] == 55


class TestInsertBronzePosTransaction:
    def test_inserts_pos_transaction(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "transaction_id": "POS-100",
            "drug_code": "DRG001",
            "net_amount": Decimal("50"),
            "loaded_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="first")
        result = repo.insert_bronze_pos_transaction(
            tenant_id=1,
            transaction_id="POS-100",
            transaction_date=datetime.datetime(2026, 4, 15),
            site_code="S1",
            register_id="T1",
            cashier_id="USR",
            customer_id=None,
            drug_code="DRG001",
            batch_number="B001",
            quantity=Decimal("2"),
            unit_price=Decimal("25"),
            net_amount=Decimal("50"),
            payment_method="cash",
        )
        assert result["transaction_id"] == "POS-100"

    def test_transaction_id_prefix_pos(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.insert_bronze_pos_transaction(
            tenant_id=1,
            transaction_id="POS-999",
            transaction_date=datetime.datetime(2026, 4, 15),
            site_code="S1",
            register_id=None,
            cashier_id="U",
            customer_id=None,
            drug_code="D",
            batch_number=None,
            quantity=Decimal("1"),
            unit_price=Decimal("10"),
            net_amount=Decimal("10"),
            payment_method="cash",
        )
        params = mock_session.execute.call_args[0][1]
        assert params["transaction_id"].startswith("POS-")

    def test_sql_uses_on_conflict_do_nothing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.insert_bronze_pos_transaction(
            tenant_id=1,
            transaction_id="POS-1",
            transaction_date=datetime.datetime(2026, 4, 15),
            site_code="S1",
            register_id=None,
            cashier_id="U",
            customer_id=None,
            drug_code="D",
            batch_number=None,
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
            net_amount=Decimal("1"),
            payment_method="cash",
        )
        sql = str(mock_session.execute.call_args[0][0])
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql

    def test_returns_empty_dict_on_duplicate(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        result = repo.insert_bronze_pos_transaction(
            tenant_id=1,
            transaction_id="POS-1",
            transaction_date=datetime.datetime(2026, 4, 15),
            site_code="S1",
            register_id=None,
            cashier_id="U",
            customer_id=None,
            drug_code="D",
            batch_number=None,
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
            net_amount=Decimal("1"),
            payment_method="cash",
        )
        assert result == {}

    def test_return_flag_passed_through(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.insert_bronze_pos_transaction(
            tenant_id=1,
            transaction_id="POS-2",
            transaction_date=datetime.datetime(2026, 4, 15),
            site_code="S1",
            register_id=None,
            cashier_id="U",
            customer_id=None,
            drug_code="D",
            batch_number=None,
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
            net_amount=Decimal("-1"),
            payment_method="cash",
            is_return=True,
        )
        params = mock_session.execute.call_args[0][1]
        assert params["is_return"] is True
