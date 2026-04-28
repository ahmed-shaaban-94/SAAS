"""Tests for shift commission + daily target (#627 Phase D4).

Acceptance criteria from the issue:

* shift with 0 items → commission = 0, transactions_so_far = 0
* shift with bonus SKUs (catalog_meta rows exist) → commission computed
* shift with non-bonus SKUs (no catalog_meta rows) → commission = 0

All three are covered below via mocked repo + service harness.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos._service_shift import ShiftCashMixin
from datapulse.pos.models.commission import ActiveShiftResponse
from datapulse.pos.repository import PosRepository

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Repository SQL fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _configure_execute(
    mock_session: MagicMock,
    rows: list[dict] | dict | None,
    *,
    mode: str,
) -> None:
    mapping_mock = MagicMock()
    if mode == "first":
        mapping_mock.first.return_value = rows
    elif mode == "all":
        mapping_mock.all.return_value = rows
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    mock_session.execute.return_value = chain


# ---------------------------------------------------------------------------
# Repo — SQL contract
# ---------------------------------------------------------------------------


class TestGetActiveShiftForStaff:
    def test_returns_open_shift(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            {
                "id": 42,
                "terminal_id": 3,
                "tenant_id": 1,
                "staff_id": "USR1",
                "shift_date": date(2026, 4, 22),
                "opened_at": datetime(2026, 4, 22, 8, tzinfo=UTC),
                "closed_at": None,
                "opening_cash": Decimal("200.00"),
                "closing_cash": None,
                "expected_cash": None,
                "variance": None,
            },
            mode="first",
        )

        shift = repo.get_active_shift_for_staff(1, "USR1")

        assert shift is not None
        assert shift["id"] == 42
        assert shift["closed_at"] is None

    def test_returns_none_when_no_open_shift(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(mock_session, None, mode="first")
        assert repo.get_active_shift_for_staff(1, "USR1") is None


class TestGetShiftCommissionSummary:
    def test_returns_zeros_for_empty_shift(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            {
                "commission_earned_egp": Decimal("0"),
                "transactions_so_far": 0,
                "sales_so_far_egp": Decimal("0"),
            },
            mode="first",
        )

        summary = repo.get_shift_commission_summary(1, tenant_id=1)
        assert summary["commission_earned_egp"] == Decimal("0")
        assert summary["transactions_so_far"] == 0

    def test_sql_left_joins_catalog_meta(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            {
                "commission_earned_egp": Decimal("12.50"),
                "transactions_so_far": 3,
                "sales_so_far_egp": Decimal("250.00"),
            },
            mode="first",
        )

        repo.get_shift_commission_summary(1, tenant_id=1)
        sql = str(mock_session.execute.call_args[0][0])
        # LEFT JOIN means drugs without a catalog_meta row contribute 0 commission,
        # so non-bonus SKUs don't block the query from returning.
        assert "LEFT" in sql and "pos.product_catalog_meta" in sql


class TestGetTerminalDailyTarget:
    def test_returns_value_when_set(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            {"daily_sales_target_egp": Decimal("5000.00")},
            mode="first",
        )
        assert repo.get_terminal_daily_target(3) == Decimal("5000.00")

    def test_returns_none_when_unset(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            {"daily_sales_target_egp": None},
            mode="first",
        )
        assert repo.get_terminal_daily_target(3) is None

    def test_returns_none_when_terminal_missing(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(mock_session, None, mode="first")
        assert repo.get_terminal_daily_target(999) is None

    def test_sql_joins_terminal_config_by_name(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        """Target must survive session open/close — joined via terminal_name, not id."""
        _configure_execute(mock_session, {"daily_sales_target_egp": None}, mode="first")
        repo.get_terminal_daily_target(3)
        sql = str(mock_session.execute.call_args[0][0])
        assert "pos.terminal_config" in sql
        assert "terminal_name" in sql


# ---------------------------------------------------------------------------
# Service — orchestration (the three issue-acceptance scenarios)
# ---------------------------------------------------------------------------


class _ServiceHarness(ShiftCashMixin):
    def __init__(self, repo: PosRepository) -> None:
        self._repo = repo
        self._verifier = None


def _mk_shift_row(**overrides: object) -> dict:
    base = {
        "id": 42,
        "terminal_id": 3,
        "tenant_id": 1,
        "staff_id": "USR1",
        "shift_date": date(2026, 4, 22),
        "opened_at": datetime(2026, 4, 22, 8, tzinfo=UTC),
        "closed_at": None,
        "opening_cash": Decimal("200.00"),
        "closing_cash": None,
        "expected_cash": None,
        "variance": None,
    }
    base.update(overrides)
    return base


class TestActiveShiftForStaff:
    def test_returns_none_when_no_open_shift(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_active_shift_for_staff.return_value = None
        svc = _ServiceHarness(mock_repo)

        result = svc.get_active_shift_for_staff(tenant_id=1, staff_id="USR1")
        assert result is None
        # Early return — never queried commission.
        mock_repo.get_shift_commission_summary.assert_not_called()

    def test_empty_shift_reports_zero_commission_and_target(self) -> None:
        """Acceptance: shift with 0 items."""
        mock_repo = MagicMock()
        mock_repo.get_active_shift_for_staff.return_value = _mk_shift_row()
        mock_repo.get_shift_commission_summary.return_value = {
            "commission_earned_egp": Decimal("0"),
            "transactions_so_far": 0,
            "sales_so_far_egp": Decimal("0"),
        }
        mock_repo.get_terminal_daily_target.return_value = None

        svc = _ServiceHarness(mock_repo)
        result = svc.get_active_shift_for_staff(tenant_id=1, staff_id="USR1")

        assert isinstance(result, ActiveShiftResponse)
        assert result.commission_earned_egp == Decimal("0")
        assert result.transactions_so_far == 0
        assert result.daily_sales_target_egp is None

    def test_shift_with_bonus_skus_reports_nonzero_commission(self) -> None:
        """Acceptance: shift with bonus SKUs — catalog_meta rows exist."""
        mock_repo = MagicMock()
        mock_repo.get_active_shift_for_staff.return_value = _mk_shift_row()
        mock_repo.get_shift_commission_summary.return_value = {
            "commission_earned_egp": Decimal("37.5000"),
            "transactions_so_far": 5,
            "sales_so_far_egp": Decimal("750.0000"),
        }
        mock_repo.get_terminal_daily_target.return_value = Decimal("5000.00")

        svc = _ServiceHarness(mock_repo)
        result = svc.get_active_shift_for_staff(tenant_id=1, staff_id="USR1")

        assert result is not None
        assert result.commission_earned_egp == Decimal("37.5000")
        assert result.transactions_so_far == 5
        assert result.sales_so_far_egp == Decimal("750.0000")
        assert result.daily_sales_target_egp == Decimal("5000.00")

    def test_shift_with_non_bonus_skus_only_reports_zero_commission(self) -> None:
        """Acceptance: shift with non-bonus SKUs — LEFT JOIN yields 0 commission."""
        mock_repo = MagicMock()
        mock_repo.get_active_shift_for_staff.return_value = _mk_shift_row()
        # Transactions happened (non-zero sales), but nothing joined to catalog_meta.
        mock_repo.get_shift_commission_summary.return_value = {
            "commission_earned_egp": Decimal("0"),
            "transactions_so_far": 3,
            "sales_so_far_egp": Decimal("450.00"),
        }
        mock_repo.get_terminal_daily_target.return_value = Decimal("5000.00")

        svc = _ServiceHarness(mock_repo)
        result = svc.get_active_shift_for_staff(tenant_id=1, staff_id="USR1")

        assert result is not None
        assert result.commission_earned_egp == Decimal("0")
        assert result.transactions_so_far == 3
        # Sales happened even though no commission — the trophy bar still progresses.
        assert result.sales_so_far_egp == Decimal("450.00")
