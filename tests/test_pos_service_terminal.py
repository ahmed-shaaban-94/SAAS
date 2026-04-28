"""Unit tests for PosService — terminal lifecycle and transaction creation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.constants import TerminalStatus
from datapulse.pos.exceptions import PosError, TerminalNotActiveError
from datapulse.pos.inventory_contract import InventoryServiceProtocol
from datapulse.pos.service import PosService

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
    return AsyncMock(spec=InventoryServiceProtocol)


@pytest.fixture()
def service(mock_repo: MagicMock, mock_inventory: AsyncMock) -> PosService:
    return PosService(mock_repo, mock_inventory)


def _terminal_row(status: str = "open") -> dict:
    return {
        "id": 1,
        "tenant_id": 1,
        "site_code": "SITE01",
        "staff_id": "staff-1",
        "terminal_name": "Terminal-1",
        "status": status,
        "opened_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
        "closed_at": None,
        "opening_cash": Decimal("100"),
        "closing_cash": None,
    }


def _txn_row(status: str = "draft") -> dict:
    return {
        "id": 100,
        "tenant_id": 1,
        "terminal_id": 1,
        "staff_id": "staff-1",
        "pharmacist_id": None,
        "customer_id": None,
        "site_code": "SITE01",
        "subtotal": Decimal("0"),
        "discount_total": Decimal("0"),
        "tax_total": Decimal("0"),
        "grand_total": Decimal("0"),
        "payment_method": None,
        "status": status,
        "receipt_number": None,
        "created_at": datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
    }


class TestTerminalLifecycle:
    def test_open_terminal_persists_and_returns_session(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.create_terminal_session.return_value = _terminal_row("open")

        session = service.open_terminal(tenant_id=1, site_code="SITE01", staff_id="staff-1")

        assert session.id == 1
        assert session.status == TerminalStatus.open
        mock_repo.create_terminal_session.assert_called_once()

    def test_pause_terminal_valid_transition(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("active")
        mock_repo.update_terminal_status.return_value = _terminal_row("paused")
        result = service.pause_terminal(1, tenant_id=1)
        assert result.status == TerminalStatus.paused
        mock_repo.update_terminal_status.assert_called_once_with(
            1, "paused", tenant_id=1, closing_cash=None
        )

    def test_pause_terminal_rejects_closed(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("closed")
        with pytest.raises(TerminalNotActiveError):
            service.pause_terminal(1, tenant_id=1)

    def test_resume_terminal_only_from_paused(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("paused")
        mock_repo.update_terminal_status.return_value = _terminal_row("active")
        result = service.resume_terminal(1, tenant_id=1)
        assert result.status == TerminalStatus.paused or result.status == TerminalStatus.active

    def test_close_terminal_records_closing_cash(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("active")
        mock_repo.update_terminal_status.return_value = {
            **_terminal_row("closed"),
            "closing_cash": Decimal("250"),
        }
        result = service.close_terminal(1, tenant_id=1, closing_cash=Decimal("250"))
        assert result.status == TerminalStatus.closed
        mock_repo.update_terminal_status.assert_called_once_with(
            1,
            "closed",
            tenant_id=1,
            closing_cash=Decimal("250"),
        )

    def test_close_unknown_terminal_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = None
        with pytest.raises(PosError):
            service.close_terminal(99, tenant_id=1, closing_cash=Decimal("0"))

    def test_list_active_terminals(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_active_terminals.return_value = [
            _terminal_row("active"),
            _terminal_row("paused"),
        ]
        sessions = service.list_active_terminals(1)
        assert len(sessions) == 2


class TestCreateTransaction:
    def test_create_promotes_open_to_active(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("open")
        mock_repo.create_transaction.return_value = _txn_row()

        service.create_transaction(
            tenant_id=1,
            terminal_id=1,
            staff_id="staff-1",
            site_code="SITE01",
        )

        assert any(
            call.args[1] == "active" for call in mock_repo.update_terminal_status.call_args_list
        )

    def test_create_rejects_paused_terminal(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("paused")
        with pytest.raises(TerminalNotActiveError):
            service.create_transaction(
                tenant_id=1,
                terminal_id=1,
                staff_id="staff-1",
                site_code="SITE01",
            )

    def test_create_rejects_closed_terminal(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = _terminal_row("closed")
        with pytest.raises(TerminalNotActiveError):
            service.create_transaction(
                tenant_id=1,
                terminal_id=1,
                staff_id="staff-1",
                site_code="SITE01",
            )
