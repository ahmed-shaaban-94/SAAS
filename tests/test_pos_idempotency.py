"""Unit tests for the POS idempotency module.

Covers: fresh-key claim, replay on identical hash, 409 on hash mismatch,
expired-row reclaim, record_response UPDATE contract, hash_body helper.

All tests use MagicMock for the DB session — no real database involvement.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def _hash(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def _past() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


def test_hash_body_is_sha256_hex() -> None:
    from datapulse.pos.idempotency import hash_body

    assert hash_body(b"hello") == hashlib.sha256(b"hello").hexdigest()


def test_check_and_claim_fresh_key_returns_replay_false() -> None:
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    # First execute (SELECT) returns no row; second (INSERT) succeeds.
    select_res = MagicMock()
    select_res.mappings.return_value.first.return_value = None
    session.execute.side_effect = [select_res, MagicMock()]

    ctx = check_and_claim(session, "k1", 1, "POST /x", _hash(b"{}"))

    assert ctx.replay is False
    assert ctx.tenant_id == 1
    assert ctx.endpoint == "POST /x"
    assert ctx.cached_status is None
    assert ctx.cached_body is None
    assert session.execute.call_count == 2


def test_check_and_claim_replays_when_hash_matches() -> None:
    from datapulse.pos.idempotency import check_and_claim

    h = _hash(b"{}")
    session = MagicMock()
    row = {
        "endpoint": "POST /x",
        "request_hash": h,
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": _future(),
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    ctx = check_and_claim(session, "k1", 1, "POST /x", h)

    assert ctx.replay is True
    assert ctx.tenant_id == 1
    assert ctx.endpoint == "POST /x"
    assert ctx.cached_status == 200
    assert ctx.cached_body == {"ok": True}


def test_check_and_claim_409_on_unrecorded_response() -> None:
    """A claimed key without a stored response must not replay as a 500 later."""
    from datapulse.pos.idempotency import check_and_claim

    h = _hash(b"{}")
    session = MagicMock()
    row = {
        "endpoint": "POST /x",
        "request_hash": h,
        "response_status": None,
        "response_body": None,
        "expires_at": _future(),
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    with pytest.raises(HTTPException) as exc:
        check_and_claim(session, "k1", 1, "POST /x", h)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Idempotency-Key request is still processing."


def test_check_and_claim_409_on_hash_mismatch() -> None:
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    row = {
        "endpoint": "POST /x",
        "request_hash": _hash(b"OLD"),
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": _future(),
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    with pytest.raises(HTTPException) as exc:
        check_and_claim(session, "k1", 1, "POST /x", _hash(b"NEW"))
    assert exc.value.status_code == 409


def test_check_and_claim_409_on_endpoint_mismatch() -> None:
    from datapulse.pos.idempotency import check_and_claim

    h = _hash(b"{}")
    session = MagicMock()
    row = {
        "endpoint": "POST /old",
        "request_hash": h,
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": _future(),
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    with pytest.raises(HTTPException) as exc:
        check_and_claim(session, "k1", 1, "POST /new", h)
    assert exc.value.status_code == 409


def test_check_and_claim_reclaims_expired_row() -> None:
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    expired_row = {
        "endpoint": "POST /x",
        "request_hash": _hash(b"{}"),
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": _past(),
    }
    select_res = MagicMock()
    select_res.mappings.return_value.first.return_value = expired_row
    # DELETE + INSERT follow the SELECT
    session.execute.side_effect = [select_res, MagicMock(), MagicMock()]

    ctx = check_and_claim(session, "k1", 1, "POST /x", _hash(b"{}"))

    assert ctx.replay is False
    assert session.execute.call_count == 3


def test_record_response_issues_update() -> None:
    from datapulse.pos.idempotency import record_response

    session = MagicMock()
    record_response(session, "k1", 200, {"ok": True}, tenant_id=7)

    session.execute.assert_called_once()
    stmt, params = session.execute.call_args.args
    assert "UPDATE pos.idempotency_keys" in str(stmt)
    assert params["key"] == "k1"
    assert params["tenant_id"] == 7
    assert params["st"] == 200
    assert params["body"] == {"ok": True}


def test_record_idempotent_success_updates_and_commits() -> None:
    from datapulse.pos.idempotency import IdempotencyContext, record_idempotent_success

    session = MagicMock()
    idem = IdempotencyContext(
        key="k1",
        tenant_id=7,
        endpoint="POST /x",
        request_hash=_hash(b"{}"),
        replay=False,
    )

    record_idempotent_success(session, idem, 201, {"ok": True})

    session.execute.assert_called_once()
    session.commit.assert_called_once()
    stmt, params = session.execute.call_args.args
    assert "UPDATE pos.idempotency_keys" in str(stmt)
    assert params["tenant_id"] == 7
    assert params["st"] == 201


def test_record_idempotent_error_rolls_back_upserts_and_commits() -> None:
    from datapulse.pos.idempotency import IdempotencyContext, record_idempotent_error

    session = MagicMock()
    idem = IdempotencyContext(
        key="k1",
        tenant_id=7,
        endpoint="POST /x",
        request_hash=_hash(b"{}"),
        replay=False,
    )

    record_idempotent_error(session, idem, status_code=409, detail="stock_low")

    session.rollback.assert_called_once()
    session.commit.assert_called_once()
    assert session.execute.call_count == 2
    stmt, params = session.execute.call_args_list[-1].args
    assert "ON CONFLICT (tenant_id, key) DO UPDATE" in str(stmt)
    assert params["key"] == "k1"
    assert params["tenant_id"] == 7
    assert params["endpoint"] == "POST /x"
    assert params["hash"] == idem.request_hash
    assert params["st"] == 409
    assert params["body"] == {"detail": "stock_low"}


def test_raise_for_replayed_error_restores_cached_http_status() -> None:
    from datapulse.pos.idempotency import IdempotencyContext, raise_for_replayed_error

    idem = IdempotencyContext(
        key="k1",
        tenant_id=7,
        endpoint="POST /x",
        request_hash=_hash(b"{}"),
        replay=True,
        cached_status=409,
        cached_body={"detail": "stock_low"},
    )

    with pytest.raises(HTTPException) as exc:
        raise_for_replayed_error(idem)

    assert exc.value.status_code == 409
    assert exc.value.detail == "stock_low"


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        pytest.param(
            __import__("datapulse.pos.exceptions", fromlist=["PosNotFoundError"]).PosNotFoundError(
                "missing", http_status=404
            ),
            404,
            id="not-found",
        ),
        pytest.param(
            __import__(
                "datapulse.pos.exceptions", fromlist=["PharmacistVerificationRequiredError"]
            ).PharmacistVerificationRequiredError("MORPHINE", "narcotic"),
            403,
            id="pharmacist",
        ),
        pytest.param(
            __import__(
                "datapulse.pos.exceptions", fromlist=["WhatsAppDisabledError"]
            ).WhatsAppDisabledError(),
            503,
            id="whatsapp-disabled",
        ),
        pytest.param(
            __import__(
                "datapulse.pos.exceptions", fromlist=["WhatsAppDeliveryFailedError"]
            ).WhatsAppDeliveryFailedError("provider down"),
            502,
            id="whatsapp-delivery",
        ),
        pytest.param(
            __import__(
                "datapulse.pos.exceptions", fromlist=["PosValidationError"]
            ).PosValidationError("bad"),
            400,
            id="validation",
        ),
        pytest.param(
            __import__("datapulse.pos.exceptions", fromlist=["PosInternalError"]).PosInternalError(
                "broken"
            ),
            500,
            id="internal",
        ),
    ],
)
def test_pos_error_status_maps_expected_exception_types(
    exc: Exception, expected_status: int
) -> None:
    from datapulse.pos.idempotency import pos_error_status

    assert pos_error_status(exc) == expected_status


def test_idempotency_dependency_is_a_factory() -> None:
    """The factory returns an awaitable dependency without side effects."""
    from datapulse.pos.idempotency import idempotency_dependency

    dep = idempotency_dependency("POST /bar")
    assert callable(dep)
