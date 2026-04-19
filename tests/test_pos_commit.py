"""atomic_commit unit tests — mocked session only.

Covers:
* Happy-path commit + change-due calc
* Cash-insufficient 400
* Non-cash payment zero change
* Receipt number format (deterministic, id-derived)
* Server-side total recomputation (H2):
    - client-inflated grand_total rejected with 400
    - client-deflated grand_total rejected with 400
    - per-item line_total recomputed server-side
* Voucher redemption:
    - amount + percent discount types
    - invalid voucher → 400
    - voucher UPDATE sets redeemed_txn_id + increments uses
    - cash insufficient after voucher still raises 400
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from datapulse.pos.constants import PaymentMethod
from datapulse.pos.models import CommitRequest, PosCartItem, VoucherStatus, VoucherType

pytestmark = pytest.mark.unit


def _payload(
    *,
    total: str = "12.00",
    tendered: str | None = "20.00",
    payment_method: PaymentMethod = PaymentMethod.cash,
    items: list[PosCartItem] | None = None,
    declared_grand_total: str | None = None,
    voucher_code: str | None = None,
    subtotal: str | None = None,
) -> CommitRequest:
    """Build a CommitRequest.

    ``declared_grand_total`` lets tests simulate a client whose declared total
    diverges from the item sum (the H2 attack surface).
    ``subtotal`` + ``voucher_code`` let voucher tests override the default
    single-item structure.
    """
    sub = subtotal if subtotal is not None else total
    if items is None:
        items = [
            PosCartItem(
                drug_code="D",
                drug_name="Drug",
                quantity=Decimal("1"),
                unit_price=Decimal(sub),
                line_total=Decimal(sub),
            )
        ]
    return CommitRequest(
        terminal_id=1,
        shift_id=1,
        staff_id="s-1",
        site_code="S1",
        items=items,
        subtotal=Decimal(sub),
        grand_total=Decimal(declared_grand_total if declared_grand_total else total),
        payment_method=payment_method,
        cash_tendered=Decimal(tendered) if tendered is not None else None,
        voucher_code=voucher_code,
    )


def _stub_session(returning_id: int) -> MagicMock:
    """Minimal MagicMock session: ``RETURNING id`` returns the configured id,
    other executes (the UPDATE + each item INSERT) are no-ops."""
    session = MagicMock()

    def _execute(stmt, params=None):  # noqa: ARG001
        sql = str(stmt)
        m = MagicMock()
        if "RETURNING id" in sql and "pos.transactions" in sql:
            m.first.return_value = (returning_id,)
        return m

    session.execute.side_effect = _execute
    return session


def test_atomic_commit_returns_response_with_change_due() -> None:
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=42)
    resp = atomic_commit(session, tenant_id=1, payload=_payload())

    assert resp.transaction_id == 42
    assert resp.receipt_number.startswith("R")
    assert "-1-42" in resp.receipt_number  # tenant-1, txn-42
    assert resp.change_due == Decimal("8.00")
    # Header INSERT + receipt UPDATE + 1 item INSERT = 3 execute calls.
    assert session.execute.call_count == 3


def test_atomic_commit_400_when_cash_insufficient() -> None:
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=42)
    with pytest.raises(HTTPException) as exc:
        atomic_commit(
            session,
            tenant_id=1,
            payload=_payload(total="50.00", tendered="10.00"),
        )
    assert exc.value.status_code == 400


def test_atomic_commit_non_cash_payment_zero_change() -> None:
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=7)
    resp = atomic_commit(
        session,
        tenant_id=1,
        payload=_payload(total="99.00", tendered=None, payment_method=PaymentMethod.card),
    )
    assert resp.change_due == Decimal("0")


def test_receipt_number_is_deterministic_from_id() -> None:
    """Regression for H2: the receipt number must include the transaction_id
    so concurrent commits can never collide (the count(*)+1 pattern could)."""
    from datapulse.pos.commit import _build_receipt_number

    now = datetime(2026, 4, 19, 12, 0, 0, tzinfo=UTC)
    rec = _build_receipt_number(tenant_id=3, transaction_id=123, now=now)
    assert rec == "R20260419-3-123"


def test_atomic_commit_rejects_inflated_client_grand_total() -> None:
    """The client sends one item for 10.00 but declares grand_total 9999.00.
    Server recomputes subtotal from items and refuses the commit."""
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=42)
    payload = _payload(
        total="10.00",
        declared_grand_total="9999.00",
        tendered="10000.00",
    )
    with pytest.raises(HTTPException) as exc:
        atomic_commit(session, tenant_id=1, payload=payload)
    assert exc.value.status_code == 400
    assert "grand_total mismatch" in str(exc.value.detail)


def test_atomic_commit_rejects_deflated_client_grand_total() -> None:
    """Mirror attack: client sends one item for 100.00 but declares
    grand_total 1.00 to understate the books. Must also be rejected."""
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=42)
    payload = _payload(
        total="100.00",
        declared_grand_total="1.00",
        tendered="100.00",
    )
    with pytest.raises(HTTPException) as exc:
        atomic_commit(session, tenant_id=1, payload=payload)
    assert exc.value.status_code == 400
    assert "grand_total mismatch" in str(exc.value.detail)


def test_atomic_commit_writes_server_computed_line_total() -> None:
    """The INSERT into transaction_items must use a server-recomputed
    line_total so a client sending line_total != unit_price*qty - discount
    can not corrupt the books."""
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=42)
    item = PosCartItem(
        drug_code="D",
        drug_name="Drug",
        quantity=Decimal("2"),
        unit_price=Decimal("50"),
        discount=Decimal("0"),
        line_total=Decimal("9999"),  # client-inflated
    )
    payload = _payload(
        total="100.00",  # subtotal = 2 * 50
        declared_grand_total="100.00",
        tendered="100.00",
        items=[item],
    )
    atomic_commit(session, tenant_id=1, payload=payload)

    # Inspect every INSERT the atomic_commit made. The transaction_items
    # INSERT must carry line_total=100 (server-recomputed), never 9999.
    item_inserts = [
        call
        for call in session.execute.call_args_list
        if "INSERT INTO pos.transaction_items" in str(call.args[0])
    ]
    assert len(item_inserts) == 1
    params = item_inserts[0].args[1]
    assert params["lt"] == Decimal("100.0000")


def test_atomic_commit_tolerates_rounding_epsilon() -> None:
    """A 0.01 EGP rounding drift between client and server must pass."""
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(returning_id=42)
    item = PosCartItem(
        drug_code="D",
        drug_name="Drug",
        quantity=Decimal("1"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("10.00"),
    )
    # Client declared 10.01 — within epsilon of server's 10.00.
    payload = _payload(
        total="10.00",
        declared_grand_total="10.01",
        tendered="20.00",
        items=[item],
    )
    resp = atomic_commit(session, tenant_id=1, payload=payload)
    assert resp.transaction_id == 42


# ---------------------------------------------------------------------------
# Voucher integration
# ---------------------------------------------------------------------------


def _voucher_response(
    *,
    discount_type: VoucherType = VoucherType.amount,
    value: Decimal = Decimal("5"),
    uses: int = 0,
    max_uses: int = 1,
    min_purchase: Decimal | None = None,
):
    from datapulse.pos.models import VoucherResponse

    return VoucherResponse(
        id=1,
        tenant_id=1,
        code="SAVE5",
        discount_type=discount_type,
        value=value,
        max_uses=max_uses,
        uses=uses,
        status=VoucherStatus.active,
        starts_at=None,
        ends_at=None,
        min_purchase=min_purchase,
        redeemed_txn_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _stub_session_with_voucher(
    *,
    returning_id: int = 42,
    voucher,
    updated_voucher=None,
) -> MagicMock:
    """Stub that understands both transaction INSERT and voucher SELECT/UPDATE."""
    session = MagicMock()
    voucher_row = {
        "id": voucher.id,
        "tenant_id": voucher.tenant_id,
        "code": voucher.code,
        "discount_type": voucher.discount_type.value,
        "value": voucher.value,
        "max_uses": voucher.max_uses,
        "uses": voucher.uses,
        "status": voucher.status.value,
        "starts_at": voucher.starts_at,
        "ends_at": voucher.ends_at,
        "min_purchase": voucher.min_purchase,
        "redeemed_txn_id": voucher.redeemed_txn_id,
        "created_at": voucher.created_at,
    }
    upd = updated_voucher or voucher
    updated_row = {
        **voucher_row,
        "uses": upd.uses,
        "status": upd.status.value,
        "redeemed_txn_id": upd.redeemed_txn_id,
    }

    def _execute(stmt, params=None):  # noqa: ARG001
        sql = str(stmt)
        m = MagicMock()
        if "RETURNING id" in sql and "pos.transactions" in sql:
            m.first.return_value = (returning_id,)
        elif "FROM pos.vouchers" in sql:
            # Handles both the pre-flight SELECT and the FOR UPDATE lock
            mappings = MagicMock()
            mappings.first.return_value = voucher_row
            m.mappings.return_value = mappings
        elif "UPDATE pos.vouchers" in sql:
            mappings = MagicMock()
            mappings.first.return_value = updated_row
            m.mappings.return_value = mappings
        return m

    session.execute.side_effect = _execute
    return session


def test_commit_with_voucher_amount_reduces_grand_total() -> None:
    from datapulse.pos.commit import atomic_commit

    voucher = _voucher_response(discount_type=VoucherType.amount, value=Decimal("5"))
    updated = _voucher_response(
        discount_type=VoucherType.amount,
        value=Decimal("5"),
        uses=1,
        max_uses=1,
    )
    updated = updated.model_copy(update={"status": VoucherStatus.redeemed, "redeemed_txn_id": 42})
    session = _stub_session_with_voucher(voucher=voucher, updated_voucher=updated)

    payload = _payload(
        subtotal="20.00",
        total="20.00",
        tendered="20.00",
        voucher_code="SAVE5",
    )
    resp = atomic_commit(session, tenant_id=1, payload=payload)

    # voucher_discount = 5, effective_grand = 20 - 5 = 15, tendered 20 -> change 5
    assert resp.voucher_discount == Decimal("5.0000")
    assert resp.change_due == Decimal("5.0000")


def test_commit_with_voucher_percent_reduces_grand_total() -> None:
    from datapulse.pos.commit import atomic_commit

    voucher = _voucher_response(discount_type=VoucherType.percent, value=Decimal("10"))
    session = _stub_session_with_voucher(voucher=voucher)

    payload = _payload(
        subtotal="100.00",
        total="100.00",
        tendered="100.00",
        voucher_code="SAVE5",
    )
    resp = atomic_commit(session, tenant_id=1, payload=payload)

    # 10% of 100 = 10, effective_grand = 90, tendered 100 -> change 10
    assert resp.voucher_discount == Decimal("10.0000")
    assert resp.change_due == Decimal("10.0000")


def test_commit_with_invalid_voucher_raises_400() -> None:
    from datapulse.pos.commit import atomic_commit

    session = MagicMock()

    def _execute(stmt, params=None):  # noqa: ARG001
        sql = str(stmt)
        m = MagicMock()
        if "FROM pos.vouchers" in sql:
            mappings = MagicMock()
            mappings.first.return_value = None
            m.mappings.return_value = mappings
        return m

    session.execute.side_effect = _execute

    payload = _payload(voucher_code="NOPE")
    with pytest.raises(HTTPException) as exc:
        atomic_commit(session, tenant_id=1, payload=payload)
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_not_found"


def test_commit_with_voucher_increments_uses_and_sets_txn_id() -> None:
    from datapulse.pos.commit import atomic_commit

    voucher = _voucher_response(max_uses=5, uses=0, value=Decimal("1"))
    updated = _voucher_response(max_uses=5, uses=1, value=Decimal("1"))
    updated = updated.model_copy(update={"redeemed_txn_id": 42})
    session = _stub_session_with_voucher(returning_id=42, voucher=voucher, updated_voucher=updated)

    payload = _payload(
        subtotal="50.00",
        total="50.00",
        tendered="50.00",
        voucher_code="SAVE5",
    )
    atomic_commit(session, tenant_id=1, payload=payload)

    # Verify UPDATE pos.vouchers was invoked with txn id 42 + new_status
    update_calls = [
        call for call in session.execute.call_args_list if "UPDATE pos.vouchers" in str(call[0][0])
    ]
    assert len(update_calls) == 1
    update_params = update_calls[0][0][1]
    assert update_params["txn"] == 42
    # uses (0) + 1 = 1 < max_uses (5) → status remains active
    assert update_params["new_status"] == "active"


def test_commit_cash_insufficient_after_voucher_still_raises_400() -> None:
    """Voucher discount reduces the bar but does not let underpaid cash through."""
    from datapulse.pos.commit import atomic_commit

    voucher = _voucher_response(discount_type=VoucherType.amount, value=Decimal("5"))
    session = _stub_session_with_voucher(voucher=voucher)

    # Subtotal 100, voucher 5 off → effective 95, tendered only 50
    payload = _payload(
        subtotal="100.00",
        total="100.00",
        tendered="50.00",
        voucher_code="SAVE5",
    )
    with pytest.raises(HTTPException) as exc:
        atomic_commit(session, tenant_id=1, payload=payload)
    assert exc.value.status_code == 400
