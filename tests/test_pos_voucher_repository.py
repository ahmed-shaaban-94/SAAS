"""VoucherRepository unit tests — mocked SQLAlchemy session only.

These tests verify SQL parameters + control-flow without touching Postgres.
Integration coverage for real FOR UPDATE semantics lives in the pipeline test
suite (DB required) and is out of scope for unit tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from datapulse.pos.models import VoucherCreate, VoucherStatus, VoucherType
from datapulse.pos.voucher_repository import VoucherRepository

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — stub the SQLAlchemy fluent chain ``session.execute(...).mappings().first()``
# ---------------------------------------------------------------------------


def _mock_exec_returning(rows: list[dict] | dict | None) -> MagicMock:
    """Build a mock that behaves like the `.mappings().first()`/`.all()` chain."""
    result = MagicMock()
    mappings = MagicMock()
    if isinstance(rows, list):
        mappings.all.return_value = rows
        mappings.first.return_value = rows[0] if rows else None
    else:
        mappings.first.return_value = rows
        mappings.all.return_value = [rows] if rows is not None else []
    result.mappings.return_value = mappings
    return result


def _row(**overrides) -> dict:
    base = {
        "id": 42,
        "tenant_id": 1,
        "code": "SAVE10",
        "discount_type": "amount",
        "value": Decimal("10"),
        "max_uses": 1,
        "uses": 0,
        "status": "active",
        "starts_at": None,
        "ends_at": None,
        "min_purchase": None,
        "redeemed_txn_id": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_returns_voucher_with_id() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec_returning(_row(id=99))
    repo = VoucherRepository(session)

    result = repo.create(
        1,
        VoucherCreate(
            code="SAVE10",
            discount_type=VoucherType.amount,
            value=Decimal("10"),
        ),
    )

    assert result.id == 99
    assert result.code == "SAVE10"
    assert result.status == VoucherStatus.active
    # Verify the INSERT was called with tenant and payload fields
    args, kwargs = session.execute.call_args
    params = args[1] if len(args) >= 2 else kwargs.get("params")
    assert params["tid"] == 1
    assert params["code"] == "SAVE10"
    assert params["dtype"] == "amount"


def test_create_duplicate_code_same_tenant_raises_integrity() -> None:
    session = MagicMock()
    session.execute.side_effect = IntegrityError("stmt", {}, Exception("duplicate"))
    repo = VoucherRepository(session)

    with pytest.raises(HTTPException) as exc:
        repo.create(
            1,
            VoucherCreate(
                code="DUPE",
                discount_type=VoucherType.amount,
                value=Decimal("5"),
            ),
        )
    assert exc.value.status_code == 409
    assert "DUPE" in exc.value.detail


# ---------------------------------------------------------------------------
# get / list
# ---------------------------------------------------------------------------


def test_get_by_code_returns_none_when_absent() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec_returning(None)
    repo = VoucherRepository(session)
    assert repo.get_by_code(1, "NOPE") is None


def test_list_for_tenant_passes_status_filter() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec_returning([])
    repo = VoucherRepository(session)

    repo.list_for_tenant(1, status=VoucherStatus.active)
    # Verify status param appears in the call
    args, _ = session.execute.call_args
    sql_text = str(args[0])
    params = args[1]
    assert "status = :status" in sql_text
    assert params["status"] == "active"


# ---------------------------------------------------------------------------
# lock_and_redeem — control flow
# ---------------------------------------------------------------------------


def _session_for_lock(first_row: dict | None, updated_row: dict | None) -> MagicMock:
    """Return a session whose two execute() calls yield first_row then updated_row."""
    session = MagicMock()
    session.execute.side_effect = [
        _mock_exec_returning(first_row),
        _mock_exec_returning(updated_row),
    ]
    return session


def test_lock_and_redeem_raises_on_missing() -> None:
    session = _session_for_lock(None, None)
    repo = VoucherRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_and_redeem(1, "X", 10, datetime.now(UTC))
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_not_found"


def test_lock_and_redeem_raises_on_inactive_voucher() -> None:
    session = _session_for_lock(_row(status="void"), None)
    repo = VoucherRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_and_redeem(1, "SAVE10", 10, datetime.now(UTC))
    assert exc.value.detail == "voucher_inactive"


def test_lock_and_redeem_raises_on_expired() -> None:
    past = datetime.now(UTC) - timedelta(days=1)
    session = _session_for_lock(_row(ends_at=past), None)
    repo = VoucherRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_and_redeem(1, "SAVE10", 10, datetime.now(UTC))
    assert exc.value.detail == "voucher_expired"


def test_lock_and_redeem_raises_on_not_yet_active() -> None:
    future = datetime.now(UTC) + timedelta(days=1)
    session = _session_for_lock(_row(starts_at=future), None)
    repo = VoucherRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_and_redeem(1, "SAVE10", 10, datetime.now(UTC))
    assert exc.value.detail == "voucher_not_yet_active"


def test_lock_and_redeem_raises_on_max_uses() -> None:
    session = _session_for_lock(_row(max_uses=2, uses=2), None)
    repo = VoucherRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_and_redeem(1, "SAVE10", 10, datetime.now(UTC))
    assert exc.value.detail == "voucher_max_uses_reached"


def test_lock_and_redeem_raises_on_min_purchase_unmet() -> None:
    session = _session_for_lock(_row(min_purchase=Decimal("100")), None)
    repo = VoucherRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_and_redeem(1, "SAVE10", 10, datetime.now(UTC), cart_subtotal=Decimal("50"))
    assert exc.value.detail == "voucher_min_purchase_unmet"


def test_lock_and_redeem_increments_uses_and_sets_txn_id() -> None:
    updated = _row(uses=1, redeemed_txn_id=777)
    session = _session_for_lock(_row(max_uses=5, uses=0), updated)
    repo = VoucherRepository(session)
    result = repo.lock_and_redeem(1, "SAVE10", 777, datetime.now(UTC))
    assert result.uses == 1
    assert result.redeemed_txn_id == 777


def test_lock_and_redeem_marks_status_redeemed_when_max_reached() -> None:
    updated = _row(max_uses=1, uses=1, status="redeemed", redeemed_txn_id=42)
    session = _session_for_lock(_row(max_uses=1, uses=0), updated)
    repo = VoucherRepository(session)
    result = repo.lock_and_redeem(1, "SAVE10", 42, datetime.now(UTC))
    assert result.status == VoucherStatus.redeemed

    # Verify the UPDATE params set status='redeemed' when uses+1 >= max_uses
    update_call = session.execute.call_args_list[1]
    args, _ = update_call
    params = args[1]
    assert params["new_status"] == "redeemed"
    assert params["txn"] == 42


def test_lock_and_redeem_keeps_status_active_when_below_max() -> None:
    updated = _row(max_uses=5, uses=1, status="active")
    session = _session_for_lock(_row(max_uses=5, uses=0), updated)
    repo = VoucherRepository(session)
    repo.lock_and_redeem(1, "SAVE10", 10, datetime.now(UTC))

    update_call = session.execute.call_args_list[1]
    args, _ = update_call
    params = args[1]
    assert params["new_status"] == "active"
