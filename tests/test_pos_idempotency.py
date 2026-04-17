"""Unit tests for the POS idempotency module.

Covers: fresh-key claim, replay on identical hash, 409 on hash mismatch,
expired-row reclaim, record_response UPDATE contract, hash_body helper.

All tests use MagicMock for the DB session — no real database involvement.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def _hash(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _future() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def _past() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=1)


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
    assert ctx.cached_status is None
    assert ctx.cached_body is None
    assert session.execute.call_count == 2


def test_check_and_claim_replays_when_hash_matches() -> None:
    from datapulse.pos.idempotency import check_and_claim

    h = _hash(b"{}")
    session = MagicMock()
    row = {
        "request_hash": h,
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": _future(),
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    ctx = check_and_claim(session, "k1", 1, "POST /x", h)

    assert ctx.replay is True
    assert ctx.cached_status == 200
    assert ctx.cached_body == {"ok": True}


def test_check_and_claim_409_on_hash_mismatch() -> None:
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    row = {
        "request_hash": _hash(b"OLD"),
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": _future(),
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    with pytest.raises(HTTPException) as exc:
        check_and_claim(session, "k1", 1, "POST /x", _hash(b"NEW"))
    assert exc.value.status_code == 409


def test_check_and_claim_reclaims_expired_row() -> None:
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    expired_row = {
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
    record_response(session, "k1", 200, {"ok": True})

    session.execute.assert_called_once()
    stmt, params = session.execute.call_args.args
    assert "UPDATE pos.idempotency_keys" in str(stmt)
    assert params["key"] == "k1"
    assert params["st"] == 200
    assert params["body"] == {"ok": True}


def test_idempotency_dependency_is_a_factory() -> None:
    """The factory returns an awaitable dependency without side effects."""
    from datapulse.pos.idempotency import idempotency_dependency

    dep = idempotency_dependency("POST /bar")
    assert callable(dep)
