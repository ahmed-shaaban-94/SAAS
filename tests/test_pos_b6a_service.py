"""Unit tests for POS B6a service methods — void, return, shift, cash events.

Strategy
--------
* Repository is mocked with MagicMock; inventory protocol with AsyncMock.
* All tests are unit-marked (no DB / Redis / network).
* Async tests use pytest-asyncio via the ``asyncio_mode = "auto"`` setting.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.constants import (
    CashDrawerEventType,
    ReturnReason,
    TransactionStatus,
)
from datapulse.pos.exceptions import PosError
from datapulse.pos.inventory_contract import (
    InventoryServiceProtocol,
    StockLevel,
    StockMovement,
)
from datapulse.pos.models import (
    PosCartItem,
    ShiftRecord,
)
from datapulse.pos.service import PosService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
    inv = AsyncMock(spec=InventoryServiceProtocol)
    inv.record_movement = AsyncMock(return_value=None)
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
    return inv


@pytest.fixture()
def service(mock_repo: MagicMock, mock_inventory: AsyncMock) -> PosService:
    return PosService(mock_repo, mock_inventory)


def _completed_txn(txn_id: int = 1, terminal_id: int = 10) -> dict:
    return {
        "id": txn_id,
        "tenant_id": 1,
        "terminal_id": terminal_id,
        "staff_id": "staff-1",
        "pharmacist_id": None,
        "customer_id": None,
        "site_code": "SITE01",
        "subtotal": Decimal("100"),
        "discount_total": Decimal("0"),
        "tax_total": Decimal("0"),
        "grand_total": Decimal("100"),
        "payment_method": "cash",
        "status": TransactionStatus.completed.value,
        "receipt_number": "R20260415-1-1",
        "created_at": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
    }


def _item_row(drug_code: str = "DRUG001", qty: str = "2") -> dict:
    return {
        "id": 1,
        "transaction_id": 1,
        "tenant_id": 1,
        "drug_code": drug_code,
        "drug_name": "Test Drug",
        "batch_number": "BATCH-1",
        "expiry_date": date(2027, 12, 31),
        "quantity": Decimal(qty),
        "unit_price": Decimal("50"),
        "discount": Decimal("0"),
        "line_total": Decimal("100"),
        "is_controlled": False,
        "pharmacist_id": None,
    }


def _shift_row(shift_id: int = 1, closed_at: datetime | None = None) -> dict:
    return {
        "id": shift_id,
        "terminal_id": 10,
        "tenant_id": 1,
        "staff_id": "staff-1",
        "shift_date": date(2026, 4, 15),
        "opened_at": datetime(2026, 4, 15, 8, 0, 0, tzinfo=UTC),
        "closed_at": closed_at,
        "opening_cash": Decimal("500"),
        "closing_cash": None,
        "expected_cash": None,
        "variance": None,
    }


# ---------------------------------------------------------------------------
# Void tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_void_transaction_success(
    service: PosService,
    mock_repo: MagicMock,
    mock_inventory: AsyncMock,
) -> None:
    txn = _completed_txn()
    item = _item_row()
    mock_repo.get_transaction.return_value = txn
    mock_repo.get_transaction_items.return_value = [item]
    mock_repo.update_transaction_status.return_value = None
    mock_repo.create_void_log.return_value = {
        "id": 99,
        "transaction_id": 1,
        "tenant_id": 1,
        "voided_by": "manager-1",
        "reason": "duplicate sale",
        "voided_at": datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
    }

    result = await service.void_transaction(
        transaction_id=1,
        tenant_id=1,
        reason="duplicate sale",
        voided_by="manager-1",
    )

    assert result.id == 99
    assert result.voided_by == "manager-1"
    assert result.transaction_id == 1

    # Inventory movement reversed before status update
    mock_inventory.record_movement.assert_awaited_once()
    call_args = mock_inventory.record_movement.call_args[0][0]
    assert isinstance(call_args, StockMovement)
    assert call_args.quantity_delta == Decimal("2")  # positive = restock
    assert call_args.movement_type == "void"

    mock_repo.update_transaction_status.assert_called_once_with(
        1, tenant_id=1, status=TransactionStatus.voided.value
    )


@pytest.mark.asyncio
async def test_void_transaction_not_found(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_transaction.return_value = None
    with pytest.raises(PosError, match="not found"):
        await service.void_transaction(
            transaction_id=999,
            tenant_id=1,
            reason="test",
            voided_by="mgr",
        )


@pytest.mark.asyncio
async def test_void_transaction_wrong_state(service: PosService, mock_repo: MagicMock) -> None:
    txn = _completed_txn()
    txn["status"] = TransactionStatus.draft.value
    mock_repo.get_transaction.return_value = txn
    with pytest.raises(PosError, match="completed transactions"):
        await service.void_transaction(
            transaction_id=1,
            tenant_id=1,
            reason="test",
            voided_by="mgr",
        )


@pytest.mark.asyncio
async def test_void_already_voided_raises(service: PosService, mock_repo: MagicMock) -> None:
    txn = _completed_txn()
    txn["status"] = TransactionStatus.voided.value
    mock_repo.get_transaction.return_value = txn
    with pytest.raises(PosError, match="completed transactions"):
        await service.void_transaction(
            transaction_id=1, tenant_id=1, reason="test", voided_by="mgr"
        )


# ---------------------------------------------------------------------------
# Return tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def return_item() -> PosCartItem:
    return PosCartItem(
        drug_code="DRUG001",
        drug_name="Test Drug",
        batch_number="BATCH-1",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("1"),
        unit_price=Decimal("50"),
        line_total=Decimal("50"),
        discount=Decimal("0"),
        is_controlled=False,
    )


def _setup_return_mocks(
    mock_repo: MagicMock,
    *,
    original_items: list[dict] | None = None,
    prior_returns: list[dict] | None = None,
    refund_amount: Decimal = Decimal("50"),
) -> None:
    """Common mock wiring for process_return happy-path tests."""
    mock_repo.get_transaction.return_value = _completed_txn()
    mock_repo.get_transaction_items.return_value = original_items or [_item_row()]
    mock_repo.get_returned_quantities_for_transaction.return_value = prior_returns or []
    mock_repo.create_transaction.return_value = {
        "id": 20,
        "tenant_id": 1,
        "terminal_id": 10,
        "staff_id": "staff-1",
        "pharmacist_id": None,
        "customer_id": None,
        "site_code": "SITE01",
        "subtotal": Decimal("0"),
        "discount_total": Decimal("0"),
        "tax_total": Decimal("0"),
        "grand_total": Decimal("0"),
        "payment_method": None,
        "status": "draft",
        "receipt_number": None,
        "created_at": datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
    }
    mock_repo.add_transaction_item.return_value = {**_item_row(), "quantity": Decimal("1")}
    mock_repo.update_transaction_status.return_value = None
    mock_repo.insert_bronze_pos_transaction.return_value = {}
    mock_repo.create_return.return_value = {
        "id": 5,
        "tenant_id": 1,
        "original_transaction_id": 1,
        "return_transaction_id": 20,
        "staff_id": "staff-1",
        "reason": ReturnReason.wrong_drug.value,
        "refund_amount": refund_amount,
        "refund_method": "cash",
        "notes": None,
        "created_at": datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
    }


@pytest.mark.asyncio
async def test_process_return_success(
    service: PosService,
    mock_repo: MagicMock,
    mock_inventory: AsyncMock,
    return_item: PosCartItem,
) -> None:
    _setup_return_mocks(mock_repo)

    result = await service.process_return(
        original_transaction_id=1,
        tenant_id=1,
        staff_id="staff-1",
        items=[return_item],
        reason=ReturnReason.wrong_drug,
        refund_method="cash",
    )

    assert result.id == 5
    assert result.original_transaction_id == 1
    assert result.return_transaction_id == 20
    assert result.refund_amount == Decimal("50")

    # Inventory restocked
    mock_inventory.record_movement.assert_awaited_once()
    mv = mock_inventory.record_movement.call_args[0][0]
    assert mv.quantity_delta == Decimal("1")  # positive
    assert mv.movement_type == "return"

    # Bronze row with is_return=True
    mock_repo.insert_bronze_pos_transaction.assert_called_once()
    call_kwargs = mock_repo.insert_bronze_pos_transaction.call_args.kwargs
    assert call_kwargs["is_return"] is True


@pytest.mark.asyncio
async def test_process_return_item_not_on_original_raises(
    service: PosService,
    mock_repo: MagicMock,
    return_item: PosCartItem,
) -> None:
    """A return item whose drug_code / batch was never on the original must
    be rejected rather than silently refunded."""
    _setup_return_mocks(mock_repo)
    rogue = PosCartItem(
        drug_code="NEVER-SOLD",
        drug_name="Spurious",
        batch_number="BATCH-1",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("1"),
        unit_price=Decimal("1000"),
        line_total=Decimal("1000"),
        discount=Decimal("0"),
        is_controlled=False,
    )
    with pytest.raises(PosError, match="not on the original"):
        await service.process_return(
            original_transaction_id=1,
            tenant_id=1,
            staff_id="staff-1",
            items=[rogue],
            reason=ReturnReason.wrong_drug,
            refund_method="cash",
        )


@pytest.mark.asyncio
async def test_process_return_quantity_exceeds_original_raises(
    service: PosService,
    mock_repo: MagicMock,
    return_item: PosCartItem,
) -> None:
    """Requesting more units than were originally sold must be rejected."""
    _setup_return_mocks(mock_repo)
    over = PosCartItem(
        drug_code="DRUG001",
        drug_name="Test Drug",
        batch_number="BATCH-1",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("99"),  # original qty is 2
        unit_price=Decimal("50"),
        line_total=Decimal("4950"),
        discount=Decimal("0"),
        is_controlled=False,
    )
    with pytest.raises(PosError, match="exceeds returnable"):
        await service.process_return(
            original_transaction_id=1,
            tenant_id=1,
            staff_id="staff-1",
            items=[over],
            reason=ReturnReason.defective,
            refund_method="cash",
        )


@pytest.mark.asyncio
async def test_process_return_blocks_cumulative_over_return(
    service: PosService,
    mock_repo: MagicMock,
    return_item: PosCartItem,
) -> None:
    """If prior returns already refunded 1 of 2 units, a second request for
    2 more units must fail because remaining = 1."""
    _setup_return_mocks(
        mock_repo,
        prior_returns=[
            {
                "drug_code": "DRUG001",
                "batch_number": "BATCH-1",
                "returned_qty": Decimal("1"),
            }
        ],
    )
    over = PosCartItem(
        drug_code="DRUG001",
        drug_name="Test Drug",
        batch_number="BATCH-1",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("2"),  # 1 already returned + 2 more > 2 sold
        unit_price=Decimal("50"),
        line_total=Decimal("100"),
        discount=Decimal("0"),
        is_controlled=False,
    )
    with pytest.raises(PosError, match="exceeds returnable"):
        await service.process_return(
            original_transaction_id=1,
            tenant_id=1,
            staff_id="staff-1",
            items=[over],
            reason=ReturnReason.defective,
            refund_method="cash",
        )


@pytest.mark.asyncio
async def test_process_return_ignores_inflated_client_line_total(
    service: PosService,
    mock_repo: MagicMock,
    mock_inventory: AsyncMock,
) -> None:
    """Client sends line_total=9999 but server recomputes from original's
    unit_price × return_qty. Refund must match server-side computation."""
    _setup_return_mocks(mock_repo)
    inflated = PosCartItem(
        drug_code="DRUG001",
        drug_name="Test Drug",
        batch_number="BATCH-1",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("1"),
        unit_price=Decimal("9999"),  # attacker-controlled
        line_total=Decimal("9999"),  # attacker-controlled
        discount=Decimal("0"),
        is_controlled=False,
    )

    await service.process_return(
        original_transaction_id=1,
        tenant_id=1,
        staff_id="staff-1",
        items=[inflated],
        reason=ReturnReason.wrong_drug,
        refund_method="cash",
    )

    # Server must have written the authoritative unit_price (50) and
    # line_total (50), NOT the client's inflated numbers.
    add_item_kwargs = mock_repo.add_transaction_item.call_args.kwargs
    assert add_item_kwargs["unit_price"] == Decimal("50")
    assert add_item_kwargs["line_total"] == Decimal("50.0000")
    create_return_kwargs = mock_repo.create_return.call_args.kwargs
    assert create_return_kwargs["refund_amount"] == Decimal("50.0000")


@pytest.mark.asyncio
async def test_process_return_duplicate_items_checked_cumulatively(
    service: PosService,
    mock_repo: MagicMock,
) -> None:
    """Submitting the same drug+batch twice in one request must sum
    quantities before the over-return check."""
    _setup_return_mocks(mock_repo)
    half = PosCartItem(
        drug_code="DRUG001",
        drug_name="Test Drug",
        batch_number="BATCH-1",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("2"),  # original qty = 2
        unit_price=Decimal("50"),
        line_total=Decimal("100"),
        discount=Decimal("0"),
        is_controlled=False,
    )
    # Two copies = 4 total, original sold 2 → must fail
    with pytest.raises(PosError, match="exceeds returnable"):
        await service.process_return(
            original_transaction_id=1,
            tenant_id=1,
            staff_id="staff-1",
            items=[half, half],
            reason=ReturnReason.defective,
            refund_method="cash",
        )


@pytest.mark.asyncio
async def test_process_return_original_not_found(
    service: PosService,
    mock_repo: MagicMock,
    return_item: PosCartItem,
) -> None:
    mock_repo.get_transaction.return_value = None
    with pytest.raises(PosError, match="not found"):
        await service.process_return(
            original_transaction_id=999,
            tenant_id=1,
            staff_id="staff-1",
            items=[return_item],
            reason=ReturnReason.defective,
            refund_method="cash",
        )


@pytest.mark.asyncio
async def test_process_return_wrong_state(
    service: PosService,
    mock_repo: MagicMock,
    return_item: PosCartItem,
) -> None:
    txn = _completed_txn()
    txn["status"] = TransactionStatus.voided.value
    mock_repo.get_transaction.return_value = txn
    with pytest.raises(PosError, match="Returns only allowed"):
        await service.process_return(
            original_transaction_id=1,
            tenant_id=1,
            staff_id="staff-1",
            items=[return_item],
            reason=ReturnReason.expired,
            refund_method="cash",
        )


@pytest.mark.asyncio
async def test_process_return_empty_items(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_transaction.return_value = _completed_txn()
    with pytest.raises(PosError, match="at least one item"):
        await service.process_return(
            original_transaction_id=1,
            tenant_id=1,
            staff_id="staff-1",
            items=[],
            reason=ReturnReason.customer_request,
            refund_method="cash",
        )


def test_get_return_not_found(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_return.return_value = None
    assert service.get_return(999, tenant_id=1) is None


def test_list_returns_for_transaction(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.list_returns_for_transaction.return_value = [
        {
            "id": 3,
            "tenant_id": 1,
            "original_transaction_id": 1,
            "return_transaction_id": 20,
            "staff_id": "staff-1",
            "reason": "defective",
            "refund_amount": Decimal("50"),
            "refund_method": "cash",
            "notes": None,
            "created_at": datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
        }
    ]
    results = service.list_returns_for_transaction(1, tenant_id=1)
    assert len(results) == 1
    assert results[0].id == 3


# ---------------------------------------------------------------------------
# Shift tests
# ---------------------------------------------------------------------------


def test_start_shift_success(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_current_shift.return_value = None
    mock_repo.create_shift_record.return_value = _shift_row()

    result = service.start_shift(
        terminal_id=10,
        tenant_id=1,
        staff_id="staff-1",
        opening_cash=Decimal("500"),
    )

    assert isinstance(result, ShiftRecord)
    assert result.id == 1
    assert result.opening_cash == Decimal("500")
    mock_repo.create_shift_record.assert_called_once()


def test_start_shift_already_open_raises(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_current_shift.return_value = _shift_row()
    with pytest.raises(PosError, match="already has an open shift"):
        service.start_shift(
            terminal_id=10,
            tenant_id=1,
            staff_id="staff-1",
        )


def test_close_shift_success(service: PosService, mock_repo: MagicMock) -> None:
    shift = _shift_row()
    mock_repo.get_shift_by_id.return_value = shift
    mock_repo.get_cash_events.return_value = [
        {
            "id": 1,
            "terminal_id": 10,
            "tenant_id": 1,
            "event_type": "sale",
            "amount": Decimal("300"),
            "reference_id": None,
            "timestamp": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
        },
        {
            "id": 2,
            "terminal_id": 10,
            "tenant_id": 1,
            "event_type": "refund",
            "amount": Decimal("50"),
            "reference_id": None,
            "timestamp": datetime(2026, 4, 15, 11, 0, 0, tzinfo=UTC),
        },
    ]
    closed_shift = {
        **shift,
        "closed_at": datetime(2026, 4, 15, 18, 0, 0, tzinfo=UTC),
        "closing_cash": Decimal("750"),
        "expected_cash": Decimal("750"),  # 500 + 300 - 50
        "variance": Decimal("0"),
    }
    mock_repo.update_shift_record.return_value = closed_shift
    mock_repo.get_shift_summary_data.return_value = {
        "transaction_count": 5,
        "total_sales": Decimal("300"),
    }

    result = service.close_shift(shift_id=1, tenant_id=1, closing_cash=Decimal("750"))

    assert result.transaction_count == 5
    assert result.total_sales == Decimal("300")
    mock_repo.update_shift_record.assert_called_once()
    # Verify expected_cash computed correctly: 500 + 300 - 50 = 750
    call_kwargs = mock_repo.update_shift_record.call_args.kwargs
    assert call_kwargs["expected_cash"] == Decimal("750")
    assert call_kwargs["variance"] == Decimal("0")  # 750 - 750


def test_close_shift_not_found(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_shift_by_id.return_value = None
    with pytest.raises(PosError, match="not found"):
        service.close_shift(shift_id=999, tenant_id=1, closing_cash=Decimal("0"))


def test_close_shift_already_closed(service: PosService, mock_repo: MagicMock) -> None:
    shift = _shift_row(closed_at=datetime(2026, 4, 15, 18, 0, 0, tzinfo=UTC))
    mock_repo.get_shift_by_id.return_value = shift
    with pytest.raises(PosError, match="already closed"):
        service.close_shift(shift_id=1, tenant_id=1, closing_cash=Decimal("750"))


def test_get_current_shift_none(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_current_shift.return_value = None
    assert service.get_current_shift(10, tenant_id=1) is None


def test_get_current_shift_found(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_current_shift.return_value = _shift_row()
    result = service.get_current_shift(10, tenant_id=1)
    assert result is not None
    assert result.id == 1


def test_list_shifts(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.list_shifts.return_value = [_shift_row()]
    results = service.list_shifts(tenant_id=1)
    assert len(results) == 1
    mock_repo.list_shifts.assert_called_once_with(1, terminal_id=None, limit=30, offset=0)


# ---------------------------------------------------------------------------
# Cash drawer event tests
# ---------------------------------------------------------------------------


def test_record_cash_event(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.record_cash_event.return_value = {
        "id": 7,
        "terminal_id": 10,
        "event_type": "float",
        "amount": Decimal("100"),
        "reference_id": None,
        "timestamp": datetime(2026, 4, 15, 8, 5, 0, tzinfo=UTC),
    }
    result = service.record_cash_event(
        terminal_id=10,
        tenant_id=1,
        event_type=CashDrawerEventType.float.value,
        amount=Decimal("100"),
    )
    assert result.id == 7
    assert result.event_type == CashDrawerEventType.float


def test_get_cash_events(service: PosService, mock_repo: MagicMock) -> None:
    mock_repo.get_cash_events.return_value = [
        {
            "id": 1,
            "terminal_id": 10,
            "event_type": "sale",
            "amount": Decimal("200"),
            "reference_id": "R1",
            "timestamp": datetime(2026, 4, 15, 9, 0, 0, tzinfo=UTC),
        }
    ]
    results = service.get_cash_events(terminal_id=10, limit=50)
    assert len(results) == 1
    assert results[0].event_type == CashDrawerEventType.sale
