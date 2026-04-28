"""M4 — get_shift_commission_summary must filter by tenant_id.

Without the tenant_id filter, two tenants sharing shift_id values could see
each other's commission totals.  The fix adds:
    AND t.tenant_id = :tenant_id
to the WHERE clause and passes it from the service caller.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _make_execute(row: dict | None, *, mode: str = "first"):
    mapping_mock = MagicMock()
    getattr(mapping_mock, mode).return_value = row
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    return chain


class TestGetShiftCommissionSummaryTenantFilter:
    """M4: tenant_id must be passed and bound in the SQL."""

    def test_method_accepts_tenant_id(self, repo: PosRepository, mock_session: MagicMock) -> None:
        """get_shift_commission_summary now requires tenant_id keyword arg."""
        mock_session.execute.return_value = _make_execute(
            {
                "commission_earned_egp": Decimal("0"),
                "transactions_so_far": 0,
                "sales_so_far_egp": Decimal("0"),
            }
        )
        # Must not raise TypeError — the signature accepts tenant_id
        result = repo.get_shift_commission_summary(shift_id=1, tenant_id=99)
        assert result is not None

    def test_tenant_id_bound_in_sql_params(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """The bound parameters dict must include tenant_id."""
        mock_session.execute.return_value = _make_execute(
            {
                "commission_earned_egp": Decimal("5.50"),
                "transactions_so_far": 2,
                "sales_so_far_egp": Decimal("120.00"),
            }
        )

        repo.get_shift_commission_summary(shift_id=7, tenant_id=42)

        _, call_kwargs = mock_session.execute.call_args
        # execute is called positionally: execute(text(...), params)
        args = mock_session.execute.call_args[0]
        bound_params = args[1]
        assert "tenant_id" in bound_params, "tenant_id must be in bound params"
        assert bound_params["tenant_id"] == 42

    def test_shift_id_bound_in_sql_params(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """shift_id must still be present in bound params."""
        mock_session.execute.return_value = _make_execute(
            {
                "commission_earned_egp": Decimal("0"),
                "transactions_so_far": 0,
                "sales_so_far_egp": Decimal("0"),
            }
        )

        repo.get_shift_commission_summary(shift_id=7, tenant_id=42)

        args = mock_session.execute.call_args[0]
        bound_params = args[1]
        assert "shift_id" in bound_params
        assert bound_params["shift_id"] == 7

    def test_tenant_id_in_sql_text(self, repo: PosRepository, mock_session: MagicMock) -> None:
        """The SQL text must reference :tenant_id."""
        mock_session.execute.return_value = _make_execute(
            {
                "commission_earned_egp": Decimal("0"),
                "transactions_so_far": 0,
                "sales_so_far_egp": Decimal("0"),
            }
        )

        repo.get_shift_commission_summary(shift_id=7, tenant_id=42)

        sql_text = str(mock_session.execute.call_args[0][0])
        assert ":tenant_id" in sql_text, "SQL must contain :tenant_id placeholder"

    def test_zeros_returned_for_empty_shift(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """Returns deterministic zeros when DB returns None row."""
        mock_session.execute.return_value = _make_execute(None)

        result = repo.get_shift_commission_summary(shift_id=99, tenant_id=1)

        assert result["commission_earned_egp"] == Decimal("0")
        assert result["transactions_so_far"] == 0
        assert result["sales_so_far_egp"] == Decimal("0")
