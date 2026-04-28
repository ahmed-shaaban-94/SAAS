"""Unit tests for PosRepository — transaction and item CRUD."""

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


def _txn_row(status: str = "draft") -> dict:
    return {
        "id": 100,
        "tenant_id": 1,
        "terminal_id": 5,
        "staff_id": "USR",
        "pharmacist_id": None,
        "customer_id": None,
        "site_code": "S1",
        "subtotal": Decimal("0"),
        "discount_total": Decimal("0"),
        "tax_total": Decimal("0"),
        "grand_total": Decimal("0"),
        "payment_method": None,
        "status": status,
        "receipt_number": None,
        "created_at": datetime.datetime(2026, 4, 15),
    }


class TestCreateTransaction:
    def test_returns_draft_transaction(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(_txn_row(), mode="one")
        result = repo.create_transaction(tenant_id=1, terminal_id=5, staff_id="USR", site_code="S1")
        assert result["id"] == 100
        assert result["status"] == "draft"

    def test_sql_inserts_draft(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(
            {
                "id": 1,
                "tenant_id": 1,
                "terminal_id": 1,
                "staff_id": "U",
                "pharmacist_id": None,
                "customer_id": None,
                "site_code": "S",
                "subtotal": Decimal("0"),
                "discount_total": Decimal("0"),
                "tax_total": Decimal("0"),
                "grand_total": Decimal("0"),
                "payment_method": None,
                "status": "draft",
                "receipt_number": None,
                "created_at": datetime.datetime(2026, 1, 1),
            },
            mode="one",
        )
        repo.create_transaction(tenant_id=1, terminal_id=1, staff_id="U", site_code="S")
        sql = str(mock_session.execute.call_args[0][0])
        assert "INSERT INTO pos.transactions" in sql
        assert "'draft'" in sql


class TestGetTransaction:
    def test_returns_row(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 55,
            "tenant_id": 2,
            "terminal_id": 3,
            "staff_id": "S",
            "pharmacist_id": None,
            "customer_id": None,
            "site_code": "X",
            "subtotal": Decimal("50"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("5"),
            "grand_total": Decimal("55"),
            "payment_method": "cash",
            "status": "completed",
            "receipt_number": "RCP-001",
            "created_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_transaction(55, tenant_id=2)
        assert result["receipt_number"] == "RCP-001"

    def test_returns_none_when_missing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_transaction(0, tenant_id=1) is None

    def test_for_update_locks_row(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 55,
            "tenant_id": 2,
            "terminal_id": 3,
            "staff_id": "S",
            "pharmacist_id": None,
            "customer_id": None,
            "site_code": "S1",
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "payment_method": None,
            "status": "completed",
            "receipt_number": "RCP-001",
            "created_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_transaction_for_update(55, tenant_id=2)
        assert result["id"] == 55
        sql = str(mock_session.execute.call_args[0][0])
        assert "FOR UPDATE" in sql


class TestListTransactions:
    def test_returns_list_filtered(self, repo: PosRepository, mock_session: MagicMock):
        rows = [
            {
                "id": 1,
                "tenant_id": 1,
                "terminal_id": 2,
                "staff_id": "U",
                "customer_id": None,
                "grand_total": Decimal("100"),
                "payment_method": "cash",
                "status": "completed",
                "receipt_number": "RCP-1",
                "created_at": datetime.datetime(2026, 4, 15),
            },
        ]
        mock_session.execute.return_value = _make_execute(rows, mode="all")
        result = repo.list_transactions(tenant_id=1, status="completed")
        assert len(result) == 1

    def test_sql_has_optional_filter(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.list_transactions(tenant_id=1, terminal_id=5)
        params = mock_session.execute.call_args[0][1]
        assert params["terminal_id"] == 5
        assert params["tenant_id"] == 1


class TestAddTransactionItem:
    def test_returns_item_row(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 10,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "DRG001",
            "drug_name": "Amoxicillin 500mg",
            "batch_number": "B001",
            "expiry_date": datetime.date(2027, 1, 1),
            "quantity": Decimal("2"),
            "unit_price": Decimal("5.00"),
            "discount": Decimal("0"),
            "line_total": Decimal("10.00"),
            "is_controlled": False,
            "pharmacist_id": None,
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.add_transaction_item(
            transaction_id=100,
            tenant_id=1,
            drug_code="DRG001",
            drug_name="Amoxicillin 500mg",
            quantity=Decimal("2"),
            unit_price=Decimal("5.00"),
            line_total=Decimal("10.00"),
        )
        assert result["line_total"] == Decimal("10.00")
        assert result["drug_code"] == "DRG001"

    def test_controlled_substance_flag(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 11,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "CTRL01",
            "drug_name": "Morphine",
            "batch_number": None,
            "expiry_date": None,
            "quantity": Decimal("1"),
            "unit_price": Decimal("50"),
            "discount": Decimal("0"),
            "line_total": Decimal("50"),
            "is_controlled": True,
            "pharmacist_id": "PHR001",
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.add_transaction_item(
            transaction_id=100,
            tenant_id=1,
            drug_code="CTRL01",
            drug_name="Morphine",
            quantity=Decimal("1"),
            unit_price=Decimal("50"),
            line_total=Decimal("50"),
            is_controlled=True,
            pharmacist_id="PHR001",
        )
        params = mock_session.execute.call_args[0][1]
        assert params["is_controlled"] is True
        assert params["pharmacist_id"] == "PHR001"
        assert result["is_controlled"] is True


class TestUpdateItemQuantity:
    def test_updates_and_returns_row(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 10,
            "transaction_id": 100,
            "drug_code": "DRG001",
            "quantity": Decimal("3"),
            "unit_price": Decimal("5.00"),
            "discount": Decimal("0"),
            "line_total": Decimal("15.00"),
            "is_controlled": False,
        }
        mock_session.execute.return_value = _make_execute(expected, mode="first")
        result = repo.update_item_quantity(
            10, tenant_id=1, quantity=Decimal("3"), unit_price=Decimal("5.00")
        )
        assert result["quantity"] == Decimal("3")

    def test_returns_none_when_missing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        result = repo.update_item_quantity(
            999, tenant_id=1, quantity=Decimal("1"), unit_price=Decimal("1")
        )
        assert result is None


class TestRemoveItem:
    def test_returns_true_on_delete(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 1
        assert repo.remove_item(10, tenant_id=1) is True

    def test_returns_false_when_not_found(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 0
        assert repo.remove_item(999, tenant_id=1) is False

    def test_sql_is_delete(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 0
        repo.remove_item(5, tenant_id=1)
        sql = str(mock_session.execute.call_args[0][0])
        assert "DELETE FROM pos.transaction_items" in sql


class TestGetTransactionItems:
    def test_returns_items_list(self, repo: PosRepository, mock_session: MagicMock):
        rows = [
            {
                "id": 1,
                "transaction_id": 10,
                "tenant_id": 1,
                "drug_code": "A",
                "drug_name": "Drug A",
                "batch_number": None,
                "expiry_date": None,
                "quantity": Decimal("1"),
                "unit_price": Decimal("10"),
                "discount": Decimal("0"),
                "line_total": Decimal("10"),
                "is_controlled": False,
                "pharmacist_id": None,
            },
        ]
        mock_session.execute.return_value = _make_execute(rows, mode="all")
        result = repo.get_transaction_items(10, tenant_id=1)
        assert len(result) == 1
        assert result[0]["drug_code"] == "A"
