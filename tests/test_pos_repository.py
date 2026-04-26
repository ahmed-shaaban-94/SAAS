"""Unit tests for PosRepository.

Tests verify SQL text contents and parameter bindings using a mocked SQLAlchemy
session. No real database connection is required.

Pattern: mock_session.execute.return_value.mappings().one/first/all()
gives control over what the repository receives from the DB driver.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> MagicMock:
    """A fully mocked SQLAlchemy Session."""
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _make_execute(rows: list[dict] | dict | None, *, mode: str = "one"):
    """Helper: configure mock_session.execute to return the given data.

    mode: 'one' | 'first' | 'all'
    """
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


# ---------------------------------------------------------------------------
# Terminal sessions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TestCreateTransaction:
    def test_returns_draft_transaction(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
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
            "status": "draft",
            "receipt_number": None,
            "created_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
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


# ---------------------------------------------------------------------------
# Transaction items
# ---------------------------------------------------------------------------


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
        result = repo.update_item_quantity(10, quantity=Decimal("3"), unit_price=Decimal("5.00"))
        assert result["quantity"] == Decimal("3")

    def test_returns_none_when_missing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        result = repo.update_item_quantity(999, quantity=Decimal("1"), unit_price=Decimal("1"))
        assert result is None


class TestRemoveItem:
    def test_returns_true_on_delete(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 1
        assert repo.remove_item(10) is True

    def test_returns_false_when_not_found(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 0
        assert repo.remove_item(999) is False

    def test_sql_is_delete(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 0
        repo.remove_item(5)
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


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


class TestSaveReceipt:
    def test_saves_thermal_receipt(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "format": "thermal",
            "file_path": None,
            "generated_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.save_receipt(transaction_id=100, tenant_id=1, fmt="thermal", content=b"\x1b@")
        assert result["format"] == "thermal"
        params = mock_session.execute.call_args[0][1]
        assert params["fmt"] == "thermal"
        assert params["content"] == b"\x1b@"

    def test_saves_pdf_receipt_with_path(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 2,
            "transaction_id": 100,
            "tenant_id": 1,
            "format": "pdf",
            "file_path": "/receipts/receipt-100.pdf",
            "generated_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.save_receipt(
            transaction_id=100,
            tenant_id=1,
            fmt="pdf",
            file_path="/receipts/receipt-100.pdf",
        )
        assert result["file_path"] == "/receipts/receipt-100.pdf"


class TestGetReceipt:
    def test_returns_most_recent_receipt(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "format": "pdf",
            "content": b"%PDF",
            "file_path": None,
            "generated_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_receipt(100, "pdf", tenant_id=1)
        assert result["content"] == b"%PDF"

    def test_returns_none_when_not_found(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_receipt(999, "thermal", tenant_id=1) is None


# ---------------------------------------------------------------------------
# Shift records
# ---------------------------------------------------------------------------


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
            closing_cash=Decimal("850"),
            expected_cash=Decimal("840"),
            variance=Decimal("10"),
            closed_at=datetime.datetime(2026, 4, 15, 18, 0),
        )
        assert result["variance"] == Decimal("10")


# ---------------------------------------------------------------------------
# Cash drawer events
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Void log
# ---------------------------------------------------------------------------


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
        result = repo.get_void_log(55)
        assert result["id"] == 1

    def test_returns_none_when_not_voided(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_void_log(100) is None


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------


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
        assert repo.get_return(1)["reason"] == "expired"

    def test_returns_none_when_missing(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_return(9999) is None


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
        result = repo.list_returns_for_transaction(55)
        assert len(result) == 2

    def test_sql_filters_by_original_txn(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.list_returns_for_transaction(55)
        params = mock_session.execute.call_args[0][1]
        assert params["original_txn_id"] == 55


# ---------------------------------------------------------------------------
# Bronze write
# ---------------------------------------------------------------------------


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
        """Ensure the 'POS-' prefix is passed (C3 collision prevention)."""
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
        assert params["transaction_id"].startswith("POS-"), (
            "transaction_id must be prefixed with 'POS-' to prevent ERP collision in fct_sales"
        )

    def test_sql_uses_on_conflict_do_nothing(self, repo: PosRepository, mock_session: MagicMock):
        """Duplicate bronze inserts must be silently ignored (idempotent)."""
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
        """ON CONFLICT DO NOTHING returns no row — repository returns empty dict."""
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


# ---------------------------------------------------------------------------
# Catalog — pharma.drug_catalog UNION coverage
# ---------------------------------------------------------------------------


class TestCatalogPharmaUnion:
    """Verify the catalog repo UNIONs ``pharma.drug_catalog`` for SAP material lookups."""

    def test_search_dim_products_unions_pharma_catalog(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.search_dim_products("para", limit=10)
        sql = str(mock_session.execute.call_args[0][0])
        assert "pharma.drug_catalog" in sql
        assert "UNION ALL" in sql
        assert "material_code" in sql
        assert "name_en" in sql
        assert "NOT EXISTS" in sql

    def test_search_dim_products_filters_catalog_with_dim_product_dups(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.search_dim_products("x")
        sql = str(mock_session.execute.call_args[0][0])
        assert "p2.drug_code = c.material_code" in sql

    def test_get_product_by_code_falls_back_to_pharma_catalog(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.get_product_by_code("500001")
        sql = str(mock_session.execute.call_args[0][0])
        assert "pharma.drug_catalog" in sql
        assert "UNION ALL" in sql
        assert "c.material_code = :drug_code" in sql

    def test_get_product_by_code_returns_dict_when_catalog_hits(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        row = {
            "drug_code": "500001",
            "drug_name": "PARACETAMOL 500MG",
            "drug_brand": "PHARCO",
            "drug_cluster": "OTC",
            "drug_category": "PAIN & FEVER",
            "unit_price": Decimal("3.6"),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_product_by_code("500001")
        assert result == row

    def test_list_catalog_products_unions_pharma_catalog(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.list_catalog_products(cursor=None, limit=200)
        sql = str(mock_session.execute.call_args[0][0])
        assert "pharma.drug_catalog" in sql
        assert "UNION ALL" in sql
        assert "combined" in sql
        assert "drug_code > :cursor" in sql
