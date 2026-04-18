"""atomic_commit unit tests — mocked session only.

Covers: happy-path commit + change-due calc, cash-insufficient 400,
non-cash payment zero change, receipt number format.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from datapulse.pos.constants import PaymentMethod
from datapulse.pos.models import CommitRequest, PosCartItem

pytestmark = pytest.mark.unit


def _payload(
    *,
    total: str = "12.00",
    tendered: str | None = "20.00",
    payment_method: PaymentMethod = PaymentMethod.cash,
) -> CommitRequest:
    return CommitRequest(
        terminal_id=1,
        shift_id=1,
        staff_id="s-1",
        site_code="S1",
        items=[
            PosCartItem(
                drug_code="D",
                drug_name="Drug",
                quantity=Decimal("1"),
                unit_price=Decimal(total),
                line_total=Decimal(total),
            )
        ],
        subtotal=Decimal(total),
        grand_total=Decimal(total),
        payment_method=payment_method,
        cash_tendered=Decimal(tendered) if tendered is not None else None,
    )


def _stub_session(receipt_seq: int, returning_id: int) -> MagicMock:
    session = MagicMock()

    def _execute(stmt, params=None):  # noqa: ARG001
        sql = str(stmt)
        m = MagicMock()
        if "count(*) + 1" in sql:
            m.scalar.return_value = receipt_seq
        elif "RETURNING id" in sql:
            m.first.return_value = (returning_id,)
        return m

    session.execute.side_effect = _execute
    return session


def test_atomic_commit_returns_response_with_change_due() -> None:
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(receipt_seq=1, returning_id=42)
    resp = atomic_commit(session, tenant_id=1, payload=_payload())

    assert resp.transaction_id == 42
    assert resp.receipt_number.startswith("R-")
    assert resp.change_due == Decimal("8.00")
    # Header INSERT + 1 item INSERT + count(*) SELECT = 3 execute calls
    assert session.execute.call_count == 3


def test_atomic_commit_400_when_cash_insufficient() -> None:
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(receipt_seq=1, returning_id=42)
    with pytest.raises(HTTPException) as exc:
        atomic_commit(session, tenant_id=1, payload=_payload(total="50.00", tendered="10.00"))
    assert exc.value.status_code == 400


def test_atomic_commit_non_cash_payment_zero_change() -> None:
    from datapulse.pos.commit import atomic_commit

    session = _stub_session(receipt_seq=1, returning_id=7)
    resp = atomic_commit(
        session,
        tenant_id=1,
        payload=_payload(total="99.00", tendered=None, payment_method=PaymentMethod.card),
    )
    assert resp.change_due == Decimal("0")


def test_receipt_number_format() -> None:
    from datapulse.pos.commit import _next_receipt_number

    session = MagicMock()
    session.execute.return_value.scalar.return_value = 42
    rec = _next_receipt_number(session, tenant_id=1)
    assert rec.startswith("R-")
    # R-YYYYMMDD-NNNNNN → 17 chars total after the leading R-
    assert len(rec) == len("R-YYYYMMDD-NNNNNN")
    assert rec.endswith("000042")
