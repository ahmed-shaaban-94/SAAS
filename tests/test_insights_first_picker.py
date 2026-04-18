"""Tests for insights_first.picker — pure priority-based selection.

Phase 2 Task 3 / #402. The picker converts a list of `InsightCandidate`
objects from different data sources into the single best `FirstInsight`
to show on the dashboard after a new user's first data load.

Priority order (first match wins):
1. mom_change    — biggest MoM revenue change (product or branch)
2. expiry_risk   — SKUs expiring within 30 days
3. stock_risk    — SKUs below reorder point
4. top_seller    — fallback: top-selling product this month
"""

from __future__ import annotations

import pytest

from datapulse.insights_first.models import FirstInsight, InsightCandidate
from datapulse.insights_first.picker import pick_best


def _candidate(kind: str, confidence: float = 0.5) -> InsightCandidate:
    return InsightCandidate(
        kind=kind,  # type: ignore[arg-type]
        title=f"{kind} title",
        body=f"{kind} body",
        action_href=f"/{kind}",
        confidence=confidence,
    )


@pytest.mark.unit
class TestPickBest:
    def test_empty_input_returns_none(self):
        assert pick_best([]) is None

    def test_all_none_returns_none(self):
        assert pick_best([None, None]) is None

    def test_single_candidate_is_returned(self):
        c = _candidate("top_seller")
        result = pick_best([c])

        assert isinstance(result, FirstInsight)
        assert result.kind == "top_seller"
        assert result.title == "top_seller title"
        assert result.action_href == "/top_seller"

    def test_mom_change_wins_over_expiry(self):
        mom = _candidate("mom_change", confidence=0.4)
        expiry = _candidate("expiry_risk", confidence=0.9)
        result = pick_best([expiry, mom])
        assert result is not None
        assert result.kind == "mom_change"

    def test_expiry_wins_over_stock_when_no_mom(self):
        expiry = _candidate("expiry_risk")
        stock = _candidate("stock_risk", confidence=0.99)
        result = pick_best([stock, expiry])
        assert result is not None
        assert result.kind == "expiry_risk"

    def test_stock_wins_over_top_seller(self):
        stock = _candidate("stock_risk")
        top = _candidate("top_seller", confidence=0.99)
        result = pick_best([top, stock])
        assert result is not None
        assert result.kind == "stock_risk"

    def test_top_seller_is_last_resort(self):
        top = _candidate("top_seller")
        result = pick_best([top])
        assert result is not None
        assert result.kind == "top_seller"

    def test_skips_none_entries(self):
        mom = _candidate("mom_change")
        result = pick_best([None, mom, None])
        assert result is not None
        assert result.kind == "mom_change"

    def test_unknown_kinds_are_ignored(self):
        """Future-proofing: unknown kinds do not crash; picker falls through."""
        unknown = _candidate("shiny_new_category")
        top = _candidate("top_seller")
        result = pick_best([unknown, top])
        assert result is not None
        assert result.kind == "top_seller"

    def test_first_candidate_of_winning_kind_is_selected(self):
        """When multiple same-kind candidates exist, the first in input order wins."""
        first = _candidate("mom_change", confidence=0.3)
        second = _candidate("mom_change", confidence=0.99)
        result = pick_best([first, second])
        assert result is not None
        assert result.confidence == 0.3

    def test_confidence_is_clamped_to_unit_interval(self):
        """InsightCandidate must reject non-[0,1] confidence so the UI
        never has to defensively clamp."""
        with pytest.raises(ValueError):
            InsightCandidate(
                kind="top_seller",
                title="t",
                body="b",
                action_href="/t",
                confidence=1.5,
            )
        with pytest.raises(ValueError):
            InsightCandidate(
                kind="top_seller",
                title="t",
                body="b",
                action_href="/t",
                confidence=-0.1,
            )
