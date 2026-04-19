"""PromotionRepository unit tests — mocked SQLAlchemy session only.

Verifies SQL parameter wiring + control flow without touching Postgres.
Integration coverage for real FOR UPDATE semantics lives in the pipeline
test suite (DB required).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from datapulse.pos.models import (
    PromotionCreate,
    PromotionDiscountType,
    PromotionScope,
    PromotionStatus,
    PromotionUpdate,
)
from datapulse.pos.promotion_repository import PromotionRepository

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — stub the SQLAlchemy fluent chain
# ---------------------------------------------------------------------------


def _mock_exec(rows: list[dict] | dict | None) -> MagicMock:
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
        "name": "Ramadan",
        "description": None,
        "discount_type": "amount",
        "value": Decimal("10"),
        "scope": "all",
        "starts_at": datetime.now(UTC) - timedelta(days=1),
        "ends_at": datetime.now(UTC) + timedelta(days=7),
        "min_purchase": None,
        "max_discount": None,
        "status": "paused",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return base


def _create_payload(**overrides) -> PromotionCreate:
    base = {
        "name": "Ramadan",
        "discount_type": PromotionDiscountType.amount,
        "value": Decimal("10"),
        "scope": PromotionScope.all,
        "starts_at": datetime.now(UTC),
        "ends_at": datetime.now(UTC) + timedelta(days=30),
    }
    base.update(overrides)
    return PromotionCreate(**base)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_returns_promotion_with_id_and_scope_lists() -> None:
    session = MagicMock()
    # Sequence: INSERT promotion → no scope writes for scope='all'
    session.execute.side_effect = [_mock_exec(_row(id=99))]
    # Stub further execute() calls (scope joins / usage stats) — empty.
    session.execute.side_effect = list(session.execute.side_effect) + [_mock_exec([])] * 10

    repo = PromotionRepository(session)
    promo = repo.create(1, _create_payload())

    assert promo.id == 99
    assert promo.scope == PromotionScope.all
    assert promo.scope_items == []
    # First INSERT is for pos.promotions with tenant + name
    first_call = session.execute.call_args_list[0]
    params = first_call.args[1]
    assert params["tid"] == 1
    assert params["name"] == "Ramadan"
    assert params["dtype"] == "amount"


def test_create_items_scope_writes_join_rows() -> None:
    session = MagicMock()
    # First: INSERT promotion; next: two INSERTs for scope_items
    session.execute.side_effect = [
        _mock_exec(_row(id=7, scope="items")),
        _mock_exec(None),
        _mock_exec(None),
    ]
    repo = PromotionRepository(session)
    promo = repo.create(
        1,
        _create_payload(scope=PromotionScope.items, scope_items=["A", "B"]),
    )
    assert promo.id == 7
    assert promo.scope_items == ["A", "B"]
    # Two scope_items INSERTs happened after the promotion INSERT
    item_inserts = [
        c for c in session.execute.call_args_list[1:]
        if "promotion_items" in str(c.args[0])
    ]
    assert len(item_inserts) == 2


def test_create_duplicate_name_raises_409() -> None:
    session = MagicMock()
    session.execute.side_effect = IntegrityError("stmt", {}, Exception("duplicate"))
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.create(1, _create_payload(name="Dupe"))
    assert exc.value.status_code == 409
    assert "Dupe" in exc.value.detail


# ---------------------------------------------------------------------------
# set_status
# ---------------------------------------------------------------------------


def test_set_status_rejects_expired() -> None:
    session = MagicMock()
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.set_status(1, 7, PromotionStatus.expired)
    assert exc.value.status_code == 400
    assert exc.value.detail == "promotion_status_invalid"


def test_set_status_not_found_raises_404() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec(None)
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.set_status(1, 7, PromotionStatus.active)
    assert exc.value.status_code == 404
    assert exc.value.detail == "promotion_not_found"


def test_set_status_active_runs_update() -> None:
    session = MagicMock()
    # UPDATE returns a row → then get() calls re-SELECT; stub everything to keep it simple.
    session.execute.side_effect = [
        _mock_exec({"id": 7}),  # UPDATE RETURNING id
        _mock_exec(_row(id=7, status="active")),  # main SELECT
        _mock_exec([]),  # scope_items
        _mock_exec([]),  # scope_categories
        _mock_exec({"n": 0, "total": Decimal("0")}),  # usage_stats
    ]
    repo = PromotionRepository(session)
    result = repo.set_status(1, 7, PromotionStatus.active)
    assert result.status == PromotionStatus.active
    update_call = session.execute.call_args_list[0]
    assert update_call.args[1]["s"] == "active"


# ---------------------------------------------------------------------------
# lock_for_application
# ---------------------------------------------------------------------------


def test_lock_for_application_raises_on_missing() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec(None)
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_for_application(1, 7, datetime.now(UTC))
    assert exc.value.status_code == 400
    assert exc.value.detail == "promotion_not_found"


def test_lock_for_application_raises_on_paused() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        _mock_exec(_row(status="paused")),
        _mock_exec([]),  # scope_items
        _mock_exec([]),  # scope_categories
    ]
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_for_application(1, 7, datetime.now(UTC))
    assert exc.value.detail == "promotion_inactive"


def test_lock_for_application_raises_on_expired_window() -> None:
    session = MagicMock()
    past = datetime.now(UTC) - timedelta(days=10)
    session.execute.side_effect = [
        _mock_exec(_row(status="active", starts_at=past - timedelta(days=5), ends_at=past)),
        _mock_exec([]),
        _mock_exec([]),
    ]
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.lock_for_application(1, 7, datetime.now(UTC))
    assert exc.value.detail == "promotion_expired"


def test_lock_for_application_succeeds_for_active_in_window() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        _mock_exec(_row(status="active")),
        _mock_exec([]),
        _mock_exec([]),
    ]
    repo = PromotionRepository(session)
    promo = repo.lock_for_application(1, 42, datetime.now(UTC))
    assert promo.id == 42


# ---------------------------------------------------------------------------
# record_application
# ---------------------------------------------------------------------------


def test_record_application_inserts_audit_row() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec(
        {
            "id": 500,
            "promotion_id": 42,
            "transaction_id": 777,
            "cashier_staff_id": "cashier-1",
            "discount_applied": Decimal("15.5000"),
            "applied_at": datetime(2026, 4, 19, tzinfo=UTC),
        }
    )
    repo = PromotionRepository(session)
    row = repo.record_application(
        tenant_id=1,
        promotion_id=42,
        transaction_id=777,
        cashier_staff_id="cashier-1",
        discount_applied=Decimal("15.5"),
        applied_at=datetime(2026, 4, 19, tzinfo=UTC),
    )
    assert row.id == 500
    assert row.discount_applied == Decimal("15.5000")
    # Verify the INSERT carries the staff + discount
    params = session.execute.call_args.args[1]
    assert params["cash"] == "cashier-1"
    assert params["txn"] == 777


# ---------------------------------------------------------------------------
# update — partial
# ---------------------------------------------------------------------------


def test_update_fails_when_promotion_missing() -> None:
    session = MagicMock()
    # get() returns None → SELECT yields no row
    session.execute.return_value = _mock_exec(None)
    repo = PromotionRepository(session)
    with pytest.raises(HTTPException) as exc:
        repo.update(1, 9, PromotionUpdate(name="Renamed"))
    assert exc.value.status_code == 404


def test_list_for_tenant_passes_status_filter() -> None:
    session = MagicMock()
    session.execute.return_value = _mock_exec([])
    repo = PromotionRepository(session)
    repo.list_for_tenant(1, status=PromotionStatus.active)
    args, _ = session.execute.call_args
    sql_text = str(args[0])
    params = args[1]
    assert "status = :status" in sql_text
    assert params["status"] == "active"
