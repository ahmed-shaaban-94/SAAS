"""Shift-close guard tests — dual-side check, forensic audit row on each outcome."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def test_guard_accepts_when_both_checks_clean() -> None:
    from datapulse.pos.shift_close_guard import enforce_close_guard

    session = MagicMock()
    session.execute.return_value.scalar.return_value = 0

    result = enforce_close_guard(
        session,
        shift_id=1,
        tenant_id=1,
        terminal_id=1,
        claim_count=0,
        claim_digest="sha256:clean",
    )
    assert result.outcome == "accepted"
    # SELECT count + INSERT accepted-row = 2 calls
    assert session.execute.call_count == 2


def test_guard_rejects_client_claim_nonzero() -> None:
    from datapulse.pos.shift_close_guard import enforce_close_guard

    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        enforce_close_guard(
            session,
            shift_id=1,
            tenant_id=1,
            terminal_id=1,
            claim_count=3,
            claim_digest="sha256:three",
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "provisional_work_pending"
    # Only the rejection-INSERT call
    assert session.execute.call_count == 1


def test_guard_rejects_server_incomplete_transactions() -> None:
    from datapulse.pos.shift_close_guard import enforce_close_guard

    session = MagicMock()
    session.execute.return_value.scalar.return_value = 2

    with pytest.raises(HTTPException) as exc:
        enforce_close_guard(
            session,
            shift_id=1,
            tenant_id=1,
            terminal_id=1,
            claim_count=0,
            claim_digest="sha256:clean",
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "server_side_incomplete_transactions"
    # SELECT + rejection-INSERT
    assert session.execute.call_count == 2
