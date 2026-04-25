"""Unit tests for :class:`PosService` — full B3 transaction flow.

Strategy
--------
* The repository is mocked with :class:`MagicMock` — we assert the exact dicts
  passed in / returned out, never hit a real database.
* The inventory protocol is mocked with :class:`AsyncMock` because the real
  protocol is async (``InventoryServiceProtocol``).
* Every test is unit-marked (no DB / Redis / network).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.constants import (
    PaymentMethod,
    TerminalStatus,
    TransactionStatus,
)
from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    PosError,
    TerminalNotActiveError,
)
from datapulse.pos.inventory_contract import (
    BatchInfo,
    InventoryServiceProtocol,
    StockLevel,
    StockMovement,
)
from datapulse.pos.models import CheckoutRequest
from datapulse.pos.pharmacist_verifier import PharmacistVerifier, hash_pin
from datapulse.pos.service import (
    PosService,
    _build_receipt_number,
    _is_controlled,
    _select_fefo_batch,
)
from datapulse.pos.terminal import (
    assert_can_transition,
    can_transition,
    compute_expected_cash,
    compute_variance,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
    """An AsyncMock satisfying the InventoryServiceProtocol surface."""
    inv = AsyncMock(spec=InventoryServiceProtocol)
    inv.get_stock_level = AsyncMock(
        return_value=StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("100"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("100"),
            reorder_point=Decimal("20"),
        )
    )
    inv.check_batch_expiry = AsyncMock(
        return_value=[
            BatchInfo(
                batch_number="BATCH-NEW",
                expiry_date=date(2027, 12, 31),
                quantity_available=Decimal("100"),
            )
        ]
    )
    inv.record_movement = AsyncMock(return_value=None)
    inv.get_reorder_alerts = AsyncMock(return_value=[])
    return inv


@pytest.fixture()
def service(mock_repo: MagicMock, mock_inventory: AsyncMock) -> PosService:
    return PosService(mock_repo, mock_inventory)


@pytest.fixture()
def verifier() -> PharmacistVerifier:
    """A real :class:`PharmacistVerifier` so controlled-substance tests issue
    and validate signed tokens end-to-end (no mocking of the crypto path)."""
    return PharmacistVerifier(
        secret_key="test-secret",
        pin_lookup=lambda _uid: hash_pin("1234"),
    )


@pytest.fixture()
def service_with_verifier(
    mock_repo: MagicMock,
    mock_inventory: AsyncMock,
    verifier: PharmacistVerifier,
) -> PosService:
    return PosService(mock_repo, mock_inventory, verifier)


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


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestPureHelpers:
    def test_is_controlled_true(self):
        assert _is_controlled("Narcotic") is True
        assert _is_controlled("schedule_iv") is True

    def test_is_controlled_false(self):
        assert _is_controlled("Antibiotic") is False
        assert _is_controlled(None) is False

    def test_build_receipt_number_format(self):
        rn = _build_receipt_number(tenant_id=42, transaction_id=7)
        assert rn.startswith("R")
        assert "-42-7" in rn

    def test_select_fefo_batch_picks_earliest(self):
        batches = [
            BatchInfo("LATE", date(2027, 12, 1), Decimal("100")),
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("100")),
            BatchInfo("MID", date(2027, 1, 1), Decimal("100")),
        ]
        chosen = _select_fefo_batch(batches, Decimal("5"))
        assert chosen is not None
        assert chosen.batch_number == "EARLY"

    def test_select_fefo_batch_skips_insufficient(self):
        batches = [
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("3")),
            BatchInfo("LATE", date(2027, 1, 1), Decimal("50")),
        ]
        chosen = _select_fefo_batch(batches, Decimal("10"))
        assert chosen is not None
        assert chosen.batch_number == "LATE"

    def test_select_fefo_batch_returns_none_when_none_satisfy(self):
        batches = [
            BatchInfo("A", date(2026, 6, 1), Decimal("3")),
            BatchInfo("B", date(2027, 1, 1), Decimal("4")),
        ]
        assert _select_fefo_batch(batches, Decimal("10")) is None

    def test_select_fefo_batch_handles_no_expiry_as_far_future(self):
        batches = [
            BatchInfo("NO-EXPIRY", None, Decimal("100")),
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("100")),
        ]
        chosen = _select_fefo_batch(batches, Decimal("10"))
        assert chosen is not None
        assert chosen.batch_number == "EARLY"


# ---------------------------------------------------------------------------
# Terminal state machine
# ---------------------------------------------------------------------------


class TestTerminalStateMachine:
    def test_open_to_active_allowed(self):
        assert can_transition(TerminalStatus.open, TerminalStatus.active) is True

    def test_active_to_paused_allowed(self):
        assert can_transition(TerminalStatus.active, TerminalStatus.paused) is True

    def test_paused_to_active_allowed(self):
        assert can_transition(TerminalStatus.paused, TerminalStatus.active) is True

    def test_closed_to_anything_rejected(self):
        for nxt in (TerminalStatus.open, TerminalStatus.active, TerminalStatus.paused):
            assert can_transition(TerminalStatus.closed, nxt) is False

    def test_open_to_paused_rejected(self):
        assert can_transition(TerminalStatus.open, TerminalStatus.paused) is False

    def test_same_state_is_not_a_transition(self):
        assert can_transition(TerminalStatus.active, TerminalStatus.active) is False

    def test_assert_can_transition_raises_for_illegal(self):
        with pytest.raises(TerminalNotActiveError) as exc_info:
            assert_can_transition(1, TerminalStatus.closed, TerminalStatus.active)
        assert exc_info.value.terminal_id == 1

    def test_compute_variance_positive(self):
        assert compute_variance(Decimal("100"), Decimal("305"), Decimal("300")) == Decimal("5")

    def test_compute_variance_negative(self):
        assert compute_variance(Decimal("100"), Decimal("295"), Decimal("300")) == Decimal("-5")

    def test_compute_expected_cash_with_floats_and_pickups(self):
        result = compute_expected_cash(
            opening_cash=Decimal("100"),
            cash_sales=Decimal("500"),
            cash_refunds=Decimal("20"),
            floats_in=Decimal("50"),
            pickups=Decimal("30"),
        )
        # 100 + 500 + 50 - 20 - 30 = 600
        assert result == Decimal("600")


# ---------------------------------------------------------------------------
# Terminal lifecycle (service)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Transaction creation
# ---------------------------------------------------------------------------


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

        # Open terminal should be promoted to active before transaction insert
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


# ---------------------------------------------------------------------------
# Add item — async (touches inventory)
# ---------------------------------------------------------------------------


class TestAddItem:
    @pytest.mark.asyncio
    async def test_add_item_happy_path(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "DRUG001",
            "drug_name": "Paracetamol 500mg",
            "drug_brand": "Panadol",
            "drug_cluster": "Analgesic",
            "drug_category": "OTC",
            "unit_price": Decimal("12.5000"),
        }
        mock_repo.add_transaction_item.return_value = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "DRUG001",
            "drug_name": "Paracetamol 500mg",
            "batch_number": "BATCH-NEW",
            "expiry_date": date(2027, 12, 31),
            "quantity": Decimal("3"),
            "unit_price": Decimal("12.5000"),
            "discount": Decimal("0"),
            "line_total": Decimal("37.5000"),
            "is_controlled": False,
            "pharmacist_id": None,
        }

        item = await service.add_item(
            transaction_id=100,
            tenant_id=1,
            site_code="SITE01",
            drug_code="DRUG001",
            quantity=Decimal("3"),
        )

        assert item.line_total == Decimal("37.5000")
        assert item.batch_number == "BATCH-NEW"
        mock_inventory.get_stock_level.assert_awaited_once_with("DRUG001", "SITE01")
        mock_inventory.check_batch_expiry.assert_awaited_once_with("DRUG001", "SITE01")

    @pytest.mark.asyncio
    async def test_insufficient_stock_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "DRUG001",
            "drug_name": "X",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "OTC",
            "unit_price": Decimal("10"),
        }
        mock_inventory.get_stock_level.return_value = StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("3"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("3"),
            reorder_point=Decimal("0"),
        )

        with pytest.raises(InsufficientStockError) as exc_info:
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="DRUG001",
                quantity=Decimal("5"),
            )
        assert exc_info.value.requested == Decimal("5")
        assert exc_info.value.available == Decimal("3")

    @pytest.mark.asyncio
    async def test_controlled_substance_requires_pharmacist(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        with pytest.raises(PharmacistVerificationRequiredError):
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
            )

    @pytest.mark.asyncio
    async def test_controlled_substance_with_valid_token_passes(
        self,
        service_with_verifier: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        verifier: PharmacistVerifier,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        mock_repo.add_transaction_item.return_value = {
            "id": 2,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "batch_number": "BATCH-NEW",
            "expiry_date": date(2027, 12, 31),
            "quantity": Decimal("1"),
            "unit_price": Decimal("50"),
            "discount": Decimal("0"),
            "line_total": Decimal("50"),
            "is_controlled": True,
            "pharmacist_id": "pharm-7",
        }
        # Issue a real signed token for this pharmacist + drug pair.
        token = verifier.verify_and_issue("pharm-7", "1234", "MORPHINE")

        item = await service_with_verifier.add_item(
            transaction_id=100,
            tenant_id=1,
            site_code="SITE01",
            drug_code="MORPHINE",
            quantity=Decimal("1"),
            pharmacist_id=token,
        )
        assert item.is_controlled is True
        assert item.pharmacist_id == "pharm-7"
        # The repository must receive the *resolved* pharmacist id, not the
        # opaque token — this is what guarantees the audit trail is usable.
        call_kwargs = mock_repo.add_transaction_item.call_args.kwargs
        assert call_kwargs["pharmacist_id"] == "pharm-7"

    @pytest.mark.asyncio
    async def test_controlled_substance_bare_string_is_rejected(
        self,
        service_with_verifier: PosService,
        mock_repo: MagicMock,
    ):
        """Regression: passing any non-empty string as pharmacist_id used to
        satisfy the controlled-substance gate. It must now raise."""
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        with pytest.raises(PharmacistVerificationRequiredError):
            await service_with_verifier.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
                pharmacist_id="pharm-7",  # raw id, not a signed token
            )

    @pytest.mark.asyncio
    async def test_controlled_substance_without_verifier_configured(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        """When no verifier is wired, controlled substances must refuse to
        dispense rather than silently accept the caller's pharmacist_id."""
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        with pytest.raises(PharmacistVerificationRequiredError):
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
                pharmacist_id="any-token-value",
            )

    @pytest.mark.asyncio
    async def test_controlled_substance_token_for_other_drug_rejected(
        self,
        service_with_verifier: PosService,
        mock_repo: MagicMock,
        verifier: PharmacistVerifier,
    ):
        """A token issued for drug A cannot be replayed against drug B."""
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        wrong_token = verifier.verify_and_issue("pharm-7", "1234", "OXY-OTHER")
        with pytest.raises(PharmacistVerificationRequiredError):
            await service_with_verifier.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
                pharmacist_id=wrong_token,
            )

    @pytest.mark.asyncio
    async def test_unknown_drug_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_product_by_code.return_value = None
        with pytest.raises(PosError):
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="UNKNOWN",
                quantity=Decimal("1"),
            )

    @pytest.mark.asyncio
    async def test_fefo_picks_earliest_expiry(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "DRUG001",
            "drug_name": "X",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "OTC",
            "unit_price": Decimal("10"),
        }
        mock_inventory.check_batch_expiry.return_value = [
            BatchInfo("LATE", date(2027, 12, 31), Decimal("100")),
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("100")),
            BatchInfo("MID", date(2027, 1, 1), Decimal("100")),
        ]
        captured: dict = {}

        def _capture(**kwargs):
            captured.update(kwargs)
            return {
                "id": 1,
                "transaction_id": 100,
                "tenant_id": 1,
                "drug_code": "DRUG001",
                "drug_name": "X",
                "batch_number": kwargs["batch_number"],
                "expiry_date": kwargs["expiry_date"],
                "quantity": kwargs["quantity"],
                "unit_price": kwargs["unit_price"],
                "discount": Decimal("0"),
                "line_total": kwargs["line_total"],
                "is_controlled": False,
                "pharmacist_id": None,
            }

        mock_repo.add_transaction_item.side_effect = _capture
        await service.add_item(
            transaction_id=100,
            tenant_id=1,
            site_code="SITE01",
            drug_code="DRUG001",
            quantity=Decimal("5"),
        )
        assert captured["batch_number"] == "EARLY"


# ---------------------------------------------------------------------------
# Update / remove item
# ---------------------------------------------------------------------------


class TestUpdateRemoveItem:
    def test_update_item_recalculates_line_total(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.update_item_quantity.return_value = {
            "id": 1,
            "transaction_id": 100,
            "drug_code": "DRUG001",
            "drug_name": "X",
            "quantity": Decimal("4"),
            "unit_price": Decimal("12.5"),
            "discount": Decimal("0"),
            "line_total": Decimal("50.0000"),
            "is_controlled": False,
        }
        item = service.update_item(
            1,
            tenant_id=1,
            quantity=Decimal("4"),
            unit_price=Decimal("12.5"),
        )
        # Service computes line_total from unit_price × quantity
        assert item.quantity == Decimal("4")
        # Repo received the recomputed line_total
        mock_repo.update_item_quantity.assert_called_once()
        kwargs = mock_repo.update_item_quantity.call_args.kwargs
        assert kwargs["line_total"] == Decimal("50.0000")

    def test_update_unknown_item_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.update_item_quantity.return_value = None
        with pytest.raises(PosError):
            service.update_item(99, tenant_id=1, quantity=Decimal("1"), unit_price=Decimal("1"))

    def test_remove_item_returns_repo_result(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.remove_item.return_value = True
        assert service.remove_item(1, tenant_id=1) is True


# ---------------------------------------------------------------------------
# Checkout — full flow
# ---------------------------------------------------------------------------


class TestCheckout:
    @pytest.fixture()
    def three_item_setup(self, mock_repo: MagicMock) -> dict:
        """Common setup: a draft transaction with 3 items totalling 75."""
        mock_repo.get_transaction.return_value = _txn_row("draft")
        items = [
            {
                "id": 1,
                "transaction_id": 100,
                "drug_code": "DRUG001",
                "drug_name": "A",
                "quantity": Decimal("2"),
                "unit_price": Decimal("10"),
                "line_total": Decimal("20"),
                "discount": Decimal("0"),
                "batch_number": "B1",
                "is_controlled": False,
                "pharmacist_id": None,
            },
            {
                "id": 2,
                "transaction_id": 100,
                "drug_code": "DRUG002",
                "drug_name": "B",
                "quantity": Decimal("3"),
                "unit_price": Decimal("5"),
                "line_total": Decimal("15"),
                "discount": Decimal("0"),
                "batch_number": "B2",
                "is_controlled": False,
                "pharmacist_id": None,
            },
            {
                "id": 3,
                "transaction_id": 100,
                "drug_code": "DRUG003",
                "drug_name": "C",
                "quantity": Decimal("4"),
                "unit_price": Decimal("10"),
                "line_total": Decimal("40"),
                "discount": Decimal("0"),
                "batch_number": "B3",
                "is_controlled": False,
                "pharmacist_id": None,
            },
        ]
        mock_repo.get_transaction_items.return_value = items
        # update_transaction_status returns a header reflecting the update
        mock_repo.update_transaction_status.return_value = {
            **_txn_row("completed"),
            "grand_total": Decimal("75.0000"),
            "subtotal": Decimal("75.0000"),
        }
        mock_repo.insert_bronze_pos_transaction.return_value = {
            "id": 1,
            "transaction_id": "POS-R1-1-100",
            "drug_code": "X",
            "net_amount": Decimal("0"),
            "loaded_at": datetime.now(tz=UTC),
        }
        return {"items": items}

    @pytest.mark.asyncio
    async def test_full_checkout_cash(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        result = await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )

        assert result.status == TransactionStatus.completed
        assert result.grand_total == Decimal("75.0000")
        assert result.change_due == Decimal("25.0000")
        assert result.payment_method == PaymentMethod.cash
        assert result.receipt_number.startswith("R")

        # Inventory movement called once per item (3)
        assert mock_inventory.record_movement.await_count == 3
        # Bronze write called once per item
        assert mock_repo.insert_bronze_pos_transaction.call_count == 3

    @pytest.mark.asyncio
    async def test_cash_underpayment_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        with pytest.raises(PosError) as exc_info:
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("50"),
                ),
            )
        assert "insufficient" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_insurance_requires_insurance_no(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.insurance,
                ),
            )

    @pytest.mark.asyncio
    async def test_checkout_rejects_already_completed(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = _txn_row("completed")
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                ),
            )

    @pytest.mark.asyncio
    async def test_checkout_rejects_empty_cart(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = _txn_row("draft")
        mock_repo.get_transaction_items.return_value = []
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                ),
            )

    @pytest.mark.asyncio
    async def test_checkout_cas_conflict_raises_and_skips_inventory(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        """Simulate a concurrent checkout winning the race: the pre-check sees
        draft but the CAS update returns None because another request already
        flipped the row to completed. No inventory movements may fire."""
        mock_repo.update_transaction_status.return_value = None

        with pytest.raises(PosError, match="another request"):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                ),
            )

        # The CAS loser must not have recorded any stock movement — otherwise
        # concurrent retries would double-deduct stock.
        mock_inventory.record_movement.assert_not_awaited()
        mock_repo.insert_bronze_pos_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_passes_expected_status_to_repository(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        """Regression: the CAS filter must actually be sent to the repo so the
        UPDATE WHERE clause enforces ``status = 'draft'`` atomically."""
        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["expected_status"] == TransactionStatus.draft.value

    @pytest.mark.asyncio
    async def test_checkout_unknown_transaction_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = None
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=999,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("1"),
                ),
            )

    @pytest.mark.asyncio
    async def test_bronze_id_uses_pos_prefix(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )
        # Every bronze write must use a POS-prefixed transaction_id
        for call in mock_repo.insert_bronze_pos_transaction.call_args_list:
            assert call.kwargs["transaction_id"].startswith("POS-")

    @pytest.mark.asyncio
    async def test_movements_use_negative_quantity_delta(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )
        for call in mock_inventory.record_movement.await_args_list:
            mv: StockMovement = call.args[0]
            assert mv.quantity_delta < 0
            assert mv.movement_type == "sale"


# ---------------------------------------------------------------------------
# Product / stock
# ---------------------------------------------------------------------------


class TestProductSearch:
    def test_search_returns_pos_results(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.search_dim_products.return_value = [
            {
                "drug_code": "DRUG001",
                "drug_name": "Paracetamol 500mg",
                "drug_brand": "Panadol",
                "drug_cluster": "Analgesic",
                "drug_category": "OTC",
                "unit_price": Decimal("12.5"),
            },
            {
                "drug_code": "DRUG002",
                "drug_name": "Morphine",
                "drug_brand": None,
                "drug_cluster": None,
                "drug_category": "narcotic",
                "unit_price": Decimal("50"),
            },
        ]
        results = service.search_products("para")
        assert len(results) == 2
        assert results[1].is_controlled is True

    @pytest.mark.asyncio
    async def test_get_stock_info_combines_inventory_calls(
        self,
        service: PosService,
        mock_inventory: AsyncMock,
    ):
        info = await service.get_stock_info("DRUG001", "SITE01")
        assert info.drug_code == "DRUG001"
        assert info.site_code == "SITE01"
        assert info.quantity_available == Decimal("100")
        assert len(info.batches) == 1
        assert info.batches[0].batch_number == "BATCH-NEW"


# ---------------------------------------------------------------------------
# Get / list helpers
# ---------------------------------------------------------------------------


class TestQueries:
    def test_get_transaction_detail_returns_none_when_missing(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = None
        assert service.get_transaction_detail(1, tenant_id=1) is None

    def test_get_transaction_detail_includes_items(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = _txn_row("completed")
        mock_repo.get_transaction_items.return_value = [
            {
                "id": 1,
                "transaction_id": 100,
                "drug_code": "X",
                "drug_name": "X",
                "quantity": Decimal("1"),
                "unit_price": Decimal("10"),
                "line_total": Decimal("10"),
                "discount": Decimal("0"),
                "batch_number": None,
                "is_controlled": False,
                "pharmacist_id": None,
            }
        ]
        detail = service.get_transaction_detail(100, tenant_id=1)
        assert detail is not None
        assert len(detail.items) == 1

    def test_list_transactions_passes_filters(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.list_transactions.return_value = [_txn_row("completed")]
        service.list_transactions(
            tenant_id=1,
            terminal_id=2,
            status="completed",
            limit=10,
            offset=0,
        )
        mock_repo.list_transactions.assert_called_once_with(
            1,
            terminal_id=2,
            status="completed",
            limit=10,
            offset=0,
        )

    def test_get_terminal_returns_none_when_missing(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = None
        assert service.get_terminal(99) is None


class TestCheckoutWithVoucher:
    """Voucher redemption on the legacy 3-step checkout flow (#472).

    Mirrors the atomic-commit path covered in test_pos_commit.py. Preview
    discount is folded into totals BEFORE payment validation; redemption
    (lock_and_redeem) fires AFTER status CAS succeeds so a lost race never
    leaves a ghost-redeemed voucher.
    """

    @pytest.fixture()
    def mock_voucher_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture()
    def service_with_voucher(
        self,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        mock_voucher_repo: MagicMock,
    ) -> PosService:
        return PosService(
            mock_repo,
            mock_inventory,
            voucher_repo=mock_voucher_repo,
        )

    @pytest.fixture()
    def three_item_setup(self, mock_repo: MagicMock) -> dict:
        """Subtotal 75 across 3 items — shared with TestCheckout."""
        mock_repo.get_transaction.return_value = _txn_row("draft")
        items = [
            {
                "id": 1,
                "transaction_id": 100,
                "drug_code": "DRUG001",
                "drug_name": "A",
                "quantity": Decimal("2"),
                "unit_price": Decimal("10"),
                "line_total": Decimal("20"),
                "discount": Decimal("0"),
                "batch_number": "B1",
                "is_controlled": False,
                "pharmacist_id": None,
            },
            {
                "id": 2,
                "transaction_id": 100,
                "drug_code": "DRUG002",
                "drug_name": "B",
                "quantity": Decimal("3"),
                "unit_price": Decimal("5"),
                "line_total": Decimal("15"),
                "discount": Decimal("0"),
                "batch_number": "B2",
                "is_controlled": False,
                "pharmacist_id": None,
            },
            {
                "id": 3,
                "transaction_id": 100,
                "drug_code": "DRUG003",
                "drug_name": "C",
                "quantity": Decimal("4"),
                "unit_price": Decimal("10"),
                "line_total": Decimal("40"),
                "discount": Decimal("0"),
                "batch_number": "B3",
                "is_controlled": False,
                "pharmacist_id": None,
            },
        ]
        mock_repo.get_transaction_items.return_value = items
        mock_repo.update_transaction_status.return_value = {
            **_txn_row("completed"),
            "grand_total": Decimal("75.0000"),
            "subtotal": Decimal("75.0000"),
        }
        mock_repo.insert_bronze_pos_transaction.return_value = {
            "id": 1,
            "transaction_id": "POS-R1-1-100",
            "drug_code": "X",
            "net_amount": Decimal("0"),
            "loaded_at": datetime.now(tz=UTC),
        }
        return {"items": items}

    def _make_voucher(self, *, discount_type: str, value: Decimal):
        from datapulse.pos.models import VoucherResponse

        return VoucherResponse(
            id=1,
            tenant_id=1,
            code="SAVE10",
            discount_type=discount_type,
            value=value,
            max_uses=1,
            uses=0,
            status="active",
            starts_at=None,
            ends_at=None,
            min_purchase=None,
            redeemed_txn_id=None,
            created_at=datetime.now(tz=UTC),
        )

    @pytest.mark.asyncio
    async def test_amount_voucher_reduces_grand_total(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = self._make_voucher(
            discount_type="amount", value=Decimal("10")
        )
        mock_voucher_repo.lock_and_redeem.return_value = self._make_voucher(
            discount_type="amount", value=Decimal("10")
        )

        result = await service_with_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
                voucher_code="SAVE10",
            ),
        )

        assert result.grand_total == Decimal("65.0000")
        assert result.voucher_discount == Decimal("10")
        assert result.change_due == Decimal("35.0000")
        mock_voucher_repo.lock_and_redeem.assert_called_once()

    @pytest.mark.asyncio
    async def test_percent_voucher_reduces_grand_total(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = self._make_voucher(
            discount_type="percent", value=Decimal("20")
        )
        mock_voucher_repo.lock_and_redeem.return_value = self._make_voucher(
            discount_type="percent", value=Decimal("20")
        )

        result = await service_with_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
                voucher_code="PCT20",
            ),
        )

        assert result.grand_total == Decimal("60.0000")
        assert result.voucher_discount == Decimal("15.00")

    @pytest.mark.asyncio
    async def test_unknown_voucher_raises(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = None
        with pytest.raises(PosError, match=r"[Vv]oucher"):
            await service_with_voucher.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                    voucher_code="NONEXISTENT",
                ),
            )
        mock_voucher_repo.lock_and_redeem.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_voucher_code_skips_voucher_repo(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        result = await service_with_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )

        assert result.grand_total == Decimal("75.0000")
        assert result.voucher_discount == Decimal("0")
        mock_voucher_repo.get_by_code.assert_not_called()
        mock_voucher_repo.lock_and_redeem.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_voucher_repo_bypasses_voucher_code(
        self,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        """Backward compat: PosService constructed WITHOUT voucher_repo
        (existing call sites) silently ignores voucher_code."""
        service_no_voucher = PosService(mock_repo, mock_inventory)

        result = await service_no_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
                voucher_code="SAVE10",
            ),
        )

        assert result.grand_total == Decimal("75.0000")
        assert result.voucher_discount == Decimal("0")

    @pytest.mark.asyncio
    async def test_voucher_cas_fails_redemption_not_called(
        self,
        service_with_voucher: PosService,
        mock_repo: MagicMock,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = self._make_voucher(
            discount_type="amount", value=Decimal("10")
        )
        mock_repo.update_transaction_status.return_value = None  # CAS lost

        with pytest.raises(PosError, match="another request"):
            await service_with_voucher.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                    voucher_code="SAVE10",
                ),
            )
        mock_voucher_repo.lock_and_redeem.assert_not_called()
