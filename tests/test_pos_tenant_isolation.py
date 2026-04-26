"""C2 tenant predicate isolation tests — issue #675.

Verifies that repository methods accepting a ``tenant_id`` parameter pass it
as an explicit SQL predicate so that, even without RLS, a query for tenant A
cannot return rows belonging to tenant B.

Pattern:
  1. The mock session returns a fixed row that carries ``tenant_id = TENANT_B``.
  2. The repository is called with ``tenant_id = TENANT_A``.
  3. We inspect the SQL text sent to ``session.execute`` and confirm it
     includes ``tenant_id = :tenant_id`` (or equivalent).
  4. We confirm the params dict carries ``TENANT_A``, not ``TENANT_B``.

No real database connection is required.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

TENANT_A = 1
TENANT_B = 2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(mock_session: MagicMock) -> PosRepository:
    repo = PosRepository.__new__(PosRepository)
    repo._session = mock_session
    return repo


def _row(extra: dict | None = None) -> dict:
    base = {"id": 99, "tenant_id": TENANT_B}
    if extra:
        base.update(extra)
    return base


def _mock_session_returning_row(row: dict) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = row
    result.mappings.return_value.one.return_value = row
    result.mappings.return_value.all.return_value = [row]
    session.execute.return_value = result
    return session


# ---------------------------------------------------------------------------
# _repo_transaction.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_transaction_includes_tenant_predicate() -> None:
    """get_transaction must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_transaction(99, tenant_id=TENANT_A)

    assert session.execute.called
    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_update_transaction_status_includes_tenant_predicate() -> None:
    """update_transaction_status must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.update_transaction_status(99, tenant_id=TENANT_A, status="completed")

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_transaction_items_includes_tenant_predicate() -> None:
    """get_transaction_items must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_transaction_items(99, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_remove_item_includes_tenant_predicate() -> None:
    """remove_item must include tenant_id to prevent cross-tenant deletion."""
    session = MagicMock()
    result = MagicMock()
    result.rowcount = 1
    session.execute.return_value = result
    repo = _make_repo(session)

    repo.remove_item(42, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_update_item_quantity_includes_tenant_predicate() -> None:
    """update_item_quantity must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.update_item_quantity(
        42, tenant_id=TENANT_A, quantity=Decimal("2"), unit_price=Decimal("10")
    )

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_receipt_includes_tenant_predicate() -> None:
    """get_receipt must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_receipt(99, "thermal", tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


# ---------------------------------------------------------------------------
# _repo_shift.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_current_shift_includes_tenant_predicate() -> None:
    """get_current_shift must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_current_shift(5, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_shift_by_id_includes_tenant_predicate() -> None:
    """get_shift_by_id must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_shift_by_id(7, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_update_shift_record_includes_tenant_predicate() -> None:
    """update_shift_record must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.update_shift_record(7, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_shift_summary_data_includes_tenant_predicate() -> None:
    """get_shift_summary_data must filter transactions by tenant_id."""
    import datetime

    session = _mock_session_returning_row({"transaction_count": 0, "total_sales": Decimal("0")})
    repo = _make_repo(session)

    now = datetime.datetime(2026, 1, 1, 8, 0)
    repo.get_shift_summary_data(5, tenant_id=TENANT_A, opened_at=now, closed_at=now)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_cash_events_includes_tenant_predicate() -> None:
    """get_cash_events must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_cash_events(5, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


# ---------------------------------------------------------------------------
# _repo_terminal.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_terminal_session_includes_tenant_predicate() -> None:
    """get_terminal_session must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_terminal_session(3, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_update_terminal_status_includes_tenant_predicate() -> None:
    """update_terminal_status must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.update_terminal_status(3, "closed", tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


# ---------------------------------------------------------------------------
# _repo_voidreturn.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_void_log_includes_tenant_predicate() -> None:
    """get_void_log must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_void_log(99, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_return_includes_tenant_predicate() -> None:
    """get_return must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_return(55, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_list_returns_for_transaction_includes_tenant_predicate() -> None:
    """list_returns_for_transaction must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.list_returns_for_transaction(99, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


@pytest.mark.unit
def test_get_returned_quantities_includes_tenant_predicate() -> None:
    """get_returned_quantities_for_transaction must filter by tenant_id."""
    session = _mock_session_returning_row(_row())
    repo = _make_repo(session)

    repo.get_returned_quantities_for_transaction(99, tenant_id=TENANT_A)

    sql_text = str(session.execute.call_args[0][0])
    assert "tenant_id" in sql_text
    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A


# ---------------------------------------------------------------------------
# Cross-tenant isolation: TENANT_A query must not receive TENANT_B data
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_transaction_tenant_a_cannot_receive_tenant_b_row() -> None:
    """If DB returns a row with tenant_id=B, the predicate we pass is still A.

    In production, the WHERE clause prevents the DB from returning B's row.
    This test confirms the param passed is TENANT_A (not TENANT_B), so the
    query would be correctly scoped in a real DB.
    """
    session = _mock_session_returning_row(_row({"tenant_id": TENANT_B}))
    repo = _make_repo(session)

    repo.get_transaction(99, tenant_id=TENANT_A)

    params = session.execute.call_args[0][1]
    # We always query with TENANT_A — we never leak TENANT_B to the DB predicate
    assert params["tenant_id"] == TENANT_A
    assert params["tenant_id"] != TENANT_B


@pytest.mark.unit
def test_get_shift_by_id_tenant_a_cannot_receive_tenant_b_row() -> None:
    session = _mock_session_returning_row(_row({"tenant_id": TENANT_B}))
    repo = _make_repo(session)

    repo.get_shift_by_id(7, tenant_id=TENANT_A)

    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A
    assert params["tenant_id"] != TENANT_B


@pytest.mark.unit
def test_get_terminal_session_tenant_a_cannot_receive_tenant_b_row() -> None:
    session = _mock_session_returning_row(_row({"tenant_id": TENANT_B}))
    repo = _make_repo(session)

    repo.get_terminal_session(3, tenant_id=TENANT_A)

    params = session.execute.call_args[0][1]
    assert params["tenant_id"] == TENANT_A
    assert params["tenant_id"] != TENANT_B
