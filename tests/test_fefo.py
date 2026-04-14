"""Tests for the FEFO batch selection algorithm."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from datapulse.expiry.fefo import BatchSelection, select_batches_fefo

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _batch(batch_number: str, expiry_date: date, quantity: float | str) -> dict:
    return {
        "batch_number": batch_number,
        "expiry_date": expiry_date,
        "current_quantity": quantity,
    }


# ------------------------------------------------------------------
# Empty / zero edge cases
# ------------------------------------------------------------------


def test_empty_batches_returns_empty_and_full_remainder():
    selected, remaining = select_batches_fefo([], Decimal("10"))
    assert selected == []
    assert remaining == Decimal("10")


def test_zero_required_quantity_returns_immediately():
    batches = [_batch("B001", date(2025, 6, 1), "100")]
    selected, remaining = select_batches_fefo(batches, Decimal("0"))
    assert selected == []
    assert remaining == Decimal("0")


def test_negative_required_quantity_returns_immediately():
    batches = [_batch("B001", date(2025, 6, 1), "100")]
    selected, remaining = select_batches_fefo(batches, Decimal("-5"))
    assert selected == []
    assert remaining == Decimal("0")


def test_all_zero_quantity_batches_returns_empty():
    batches = [
        _batch("B001", date(2025, 6, 1), "0"),
        _batch("B002", date(2025, 7, 1), "0"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("50"))
    assert selected == []
    assert remaining == Decimal("50")


# ------------------------------------------------------------------
# Single batch — full fulfillment
# ------------------------------------------------------------------


def test_single_batch_exact_fulfillment():
    batches = [_batch("B001", date(2025, 6, 1), "100")]
    selected, remaining = select_batches_fefo(batches, Decimal("100"))
    assert len(selected) == 1
    assert selected[0].batch_number == "B001"
    assert selected[0].allocated_quantity == Decimal("100")
    assert remaining == Decimal("0")


def test_single_batch_partial_fulfillment():
    """Single batch has more than needed — only allocate what's required."""
    batches = [_batch("B001", date(2025, 6, 1), "200")]
    selected, remaining = select_batches_fefo(batches, Decimal("75"))
    assert len(selected) == 1
    assert selected[0].allocated_quantity == Decimal("75")
    assert selected[0].available_quantity == Decimal("200")
    assert remaining == Decimal("0")


def test_single_batch_insufficient_stock():
    """Single batch has less than needed — partial fulfillment with remainder."""
    batches = [_batch("B001", date(2025, 6, 1), "30")]
    selected, remaining = select_batches_fefo(batches, Decimal("100"))
    assert len(selected) == 1
    assert selected[0].allocated_quantity == Decimal("30")
    assert remaining == Decimal("70")


# ------------------------------------------------------------------
# Multi-batch — FEFO order enforcement
# ------------------------------------------------------------------


def test_multi_batch_selects_earliest_expiry_first():
    """Earliest-expiring batch must be selected first regardless of list order."""
    batches = [
        _batch("B_LATE", date(2025, 12, 1), "100"),
        _batch("B_EARLY", date(2025, 3, 1), "100"),
        _batch("B_MID", date(2025, 6, 1), "100"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("50"))
    assert len(selected) == 1
    assert selected[0].batch_number == "B_EARLY"
    assert remaining == Decimal("0")


def test_multi_batch_full_fulfillment_across_two():
    batches = [
        _batch("B001", date(2025, 3, 1), "40"),
        _batch("B002", date(2025, 6, 1), "60"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("80"))
    assert len(selected) == 2
    assert selected[0].batch_number == "B001"
    assert selected[0].allocated_quantity == Decimal("40")
    assert selected[1].batch_number == "B002"
    assert selected[1].allocated_quantity == Decimal("40")
    assert remaining == Decimal("0")


def test_multi_batch_partial_second_batch():
    """First batch fully consumed, second partially consumed."""
    batches = [
        _batch("B001", date(2025, 3, 1), "30"),
        _batch("B002", date(2025, 5, 1), "200"),
        _batch("B003", date(2025, 9, 1), "100"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("80"))
    assert len(selected) == 2
    assert selected[0].batch_number == "B001"
    assert selected[0].allocated_quantity == Decimal("30")
    assert selected[1].batch_number == "B002"
    assert selected[1].allocated_quantity == Decimal("50")
    assert remaining == Decimal("0")


def test_multi_batch_insufficient_across_all():
    """Not enough total stock across all batches."""
    batches = [
        _batch("B001", date(2025, 3, 1), "10"),
        _batch("B002", date(2025, 5, 1), "20"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("100"))
    assert len(selected) == 2
    total_allocated = sum(s.allocated_quantity for s in selected)
    assert total_allocated == Decimal("30")
    assert remaining == Decimal("70")


def test_multi_batch_three_batches_exact():
    batches = [
        _batch("B001", date(2025, 2, 1), "25"),
        _batch("B002", date(2025, 4, 1), "25"),
        _batch("B003", date(2025, 6, 1), "50"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("100"))
    assert len(selected) == 3
    assert remaining == Decimal("0")
    assert selected[0].batch_number == "B001"
    assert selected[2].batch_number == "B003"


# ------------------------------------------------------------------
# Decimal precision
# ------------------------------------------------------------------


def test_decimal_precision_maintained():
    batches = [_batch("B001", date(2025, 6, 1), "33.333")]
    selected, remaining = select_batches_fefo(batches, Decimal("10.000"))
    assert selected[0].allocated_quantity == Decimal("10.000")
    assert remaining == Decimal("0")


def test_string_quantity_converted_to_decimal():
    batches = [_batch("B001", date(2025, 6, 1), "50.5")]
    selected, remaining = select_batches_fefo(batches, Decimal("50.5"))
    assert selected[0].allocated_quantity == Decimal("50.5")
    assert remaining == Decimal("0")


# ------------------------------------------------------------------
# BatchSelection is frozen
# ------------------------------------------------------------------


def test_batch_selection_is_immutable():
    sel = BatchSelection(
        batch_number="B001",
        expiry_date=date(2025, 6, 1),
        available_quantity=Decimal("100"),
        allocated_quantity=Decimal("50"),
    )
    with pytest.raises((AttributeError, TypeError)):
        sel.batch_number = "CHANGED"  # type: ignore[misc]


# ------------------------------------------------------------------
# FEFO stops as soon as remaining is fulfilled
# ------------------------------------------------------------------


def test_fefo_stops_when_fulfilled():
    """Batches after fulfillment point must not be included."""
    batches = [
        _batch("B001", date(2025, 3, 1), "100"),
        _batch("B002", date(2025, 5, 1), "100"),
        _batch("B003", date(2025, 9, 1), "100"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("100"))
    assert len(selected) == 1
    assert selected[0].batch_number == "B001"
    assert remaining == Decimal("0")


def test_fefo_skips_zero_quantity_batches_in_middle():
    """Zero-quantity batches in the middle of the list must be skipped."""
    batches = [
        _batch("B001", date(2025, 3, 1), "0"),
        _batch("B002", date(2025, 5, 1), "0"),
        _batch("B003", date(2025, 6, 1), "50"),
    ]
    selected, remaining = select_batches_fefo(batches, Decimal("30"))
    assert len(selected) == 1
    assert selected[0].batch_number == "B003"
    assert remaining == Decimal("0")
