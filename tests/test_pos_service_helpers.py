"""Unit tests for PosService — pure helpers and terminal state machine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from datapulse.pos.constants import TerminalStatus
from datapulse.pos.exceptions import TerminalNotActiveError
from datapulse.pos.inventory_contract import BatchInfo
from datapulse.pos.service import (
    _build_receipt_number,
    _is_controlled,
    _select_fefo_batch,
)
from datapulse.pos.terminal import (
    assert_can_transition,
    can_transition,
    compute_expected_cash,
    compute_variance,
)

pytestmark = pytest.mark.unit


class TestPureHelpers:
    def test_is_controlled_true(self):
        assert _is_controlled("Narcotic") is True
        assert _is_controlled("schedule_iv") is True

    def test_is_controlled_false(self):
        assert _is_controlled("Antibiotic") is False
        assert _is_controlled(None) is False

    def test_build_receipt_number_format(self):
        rn = _build_receipt_number(tenant_id=42, transaction_id=7)
        assert rn.startswith("R")
        assert "-42-7" in rn

    def test_select_fefo_batch_picks_earliest(self):
        batches = [
            BatchInfo("LATE", date(2027, 12, 1), Decimal("100")),
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("100")),
            BatchInfo("MID", date(2027, 1, 1), Decimal("100")),
        ]
        chosen = _select_fefo_batch(batches, Decimal("5"))
        assert chosen is not None
        assert chosen.batch_number == "EARLY"

    def test_select_fefo_batch_skips_insufficient(self):
        batches = [
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("3")),
            BatchInfo("LATE", date(2027, 1, 1), Decimal("50")),
        ]
        chosen = _select_fefo_batch(batches, Decimal("10"))
        assert chosen is not None
        assert chosen.batch_number == "LATE"

    def test_select_fefo_batch_returns_none_when_none_satisfy(self):
        batches = [
            BatchInfo("A", date(2026, 6, 1), Decimal("3")),
            BatchInfo("B", date(2027, 1, 1), Decimal("4")),
        ]
        assert _select_fefo_batch(batches, Decimal("10")) is None

    def test_select_fefo_batch_handles_no_expiry_as_far_future(self):
        batches = [
            BatchInfo("NO-EXPIRY", None, Decimal("100")),
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("100")),
        ]
        chosen = _select_fefo_batch(batches, Decimal("10"))
        assert chosen is not None
        assert chosen.batch_number == "EARLY"


class TestTerminalStateMachine:
    def test_open_to_active_allowed(self):
        assert can_transition(TerminalStatus.open, TerminalStatus.active) is True

    def test_active_to_paused_allowed(self):
        assert can_transition(TerminalStatus.active, TerminalStatus.paused) is True

    def test_paused_to_active_allowed(self):
        assert can_transition(TerminalStatus.paused, TerminalStatus.active) is True

    def test_closed_to_anything_rejected(self):
        for nxt in (TerminalStatus.open, TerminalStatus.active, TerminalStatus.paused):
            assert can_transition(TerminalStatus.closed, nxt) is False

    def test_open_to_paused_rejected(self):
        assert can_transition(TerminalStatus.open, TerminalStatus.paused) is False

    def test_same_state_is_not_a_transition(self):
        assert can_transition(TerminalStatus.active, TerminalStatus.active) is False

    def test_assert_can_transition_raises_for_illegal(self):
        with pytest.raises(TerminalNotActiveError) as exc_info:
            assert_can_transition(1, TerminalStatus.closed, TerminalStatus.active)
        assert exc_info.value.terminal_id == 1

    def test_compute_variance_positive(self):
        assert compute_variance(Decimal("100"), Decimal("305"), Decimal("300")) == Decimal("5")

    def test_compute_variance_negative(self):
        assert compute_variance(Decimal("100"), Decimal("295"), Decimal("300")) == Decimal("-5")

    def test_compute_expected_cash_with_floats_and_pickups(self):
        result = compute_expected_cash(
            opening_cash=Decimal("100"),
            cash_sales=Decimal("500"),
            cash_refunds=Decimal("20"),
            floats_in=Decimal("50"),
            pickups=Decimal("30"),
        )
        assert result == Decimal("600")
