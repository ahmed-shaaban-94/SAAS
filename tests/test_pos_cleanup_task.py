"""Idempotency cleanup task tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_cleanup_executes_delete_and_returns_rowcount() -> None:
    from datapulse.tasks.cleanup_pos_idempotency import run

    session = MagicMock()
    session.execute.return_value.rowcount = 5

    deleted = run(session)

    assert deleted == 5
    session.execute.assert_called_once()
    stmt = session.execute.call_args.args[0]
    assert "DELETE FROM pos.idempotency_keys" in str(stmt)


def test_cleanup_returns_zero_when_no_rows() -> None:
    from datapulse.tasks.cleanup_pos_idempotency import run

    session = MagicMock()
    session.execute.return_value.rowcount = 0
    assert run(session) == 0


def test_cleanup_handles_none_rowcount() -> None:
    from datapulse.tasks.cleanup_pos_idempotency import run

    session = MagicMock()
    session.execute.return_value.rowcount = None
    assert run(session) == 0
