"""Tests for `fetch_mom_change_candidate` — Phase 2 follow-up #2 / #402.

The fetcher queries `bronze.sales` for the biggest month-over-month revenue
swing (product OR branch) and returns one `InsightCandidate` or None.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.insights_first.models import InsightCandidate
from datapulse.insights_first.repository import fetch_mom_change_candidate


def _session_with_row(row: dict | None) -> MagicMock:
    """Helper: return a MagicMock session whose execute().mappings().fetchone()
    returns *row*."""
    session = MagicMock()
    exec_result = MagicMock()
    mappings = MagicMock()
    mappings.fetchone.return_value = row
    exec_result.mappings.return_value = mappings
    session.execute.return_value = exec_result
    return session


def _session_that_raises(exc: Exception) -> MagicMock:
    session = MagicMock()
    session.execute.side_effect = exc
    return session


@pytest.mark.unit
class TestFetchMomChangeCandidate:
    def test_returns_none_when_no_data(self):
        session = _session_with_row(None)
        assert fetch_mom_change_candidate(session, tenant_id=1) is None

    def test_returns_none_when_previous_month_revenue_is_zero(self):
        """Division by zero is silently handled as no-signal."""
        session = _session_with_row(
            {
                "dimension": "product",
                "label": "Paracetamol 500mg Tab",
                "current_revenue": 1000.0,
                "previous_revenue": 0.0,
                "mom_pct": None,
            }
        )
        assert fetch_mom_change_candidate(session, tenant_id=1) is None

    def test_returns_candidate_for_biggest_product_swing(self):
        session = _session_with_row(
            {
                "dimension": "product",
                "label": "Paracetamol 500mg Tab",
                "current_revenue": 15000.0,
                "previous_revenue": 10000.0,
                "mom_pct": 0.5,
            }
        )
        c = fetch_mom_change_candidate(session, tenant_id=1)
        assert isinstance(c, InsightCandidate)
        assert c.kind == "mom_change"
        assert "Paracetamol" in c.title
        assert "50%" in c.title or "+50" in c.title or "50" in c.title
        assert "up" in c.body.lower() or "+" in c.body or "increase" in c.body.lower()

    def test_returns_candidate_for_negative_swing(self):
        session = _session_with_row(
            {
                "dimension": "site",
                "label": "Cairo Downtown",
                "current_revenue": 5000.0,
                "previous_revenue": 10000.0,
                "mom_pct": -0.5,
            }
        )
        c = fetch_mom_change_candidate(session, tenant_id=1)
        assert c is not None
        assert c.kind == "mom_change"
        assert (
            "down" in c.body.lower()
            or "-" in c.body
            or "decrease" in c.body.lower()
            or "drop" in c.body.lower()
        )

    def test_product_candidate_links_to_products_page(self):
        session = _session_with_row(
            {
                "dimension": "product",
                "label": "Paracetamol 500mg Tab",
                "current_revenue": 15000.0,
                "previous_revenue": 10000.0,
                "mom_pct": 0.5,
            }
        )
        c = fetch_mom_change_candidate(session, tenant_id=1)
        assert c is not None
        assert c.action_href.startswith("/products")

    def test_site_candidate_links_to_sites_page(self):
        session = _session_with_row(
            {
                "dimension": "site",
                "label": "Cairo Downtown",
                "current_revenue": 15000.0,
                "previous_revenue": 10000.0,
                "mom_pct": 0.5,
            }
        )
        c = fetch_mom_change_candidate(session, tenant_id=1)
        assert c is not None
        assert c.action_href.startswith("/sites")

    def test_confidence_scales_with_magnitude_and_clamps(self):
        # Small swing → low confidence but ≥ floor.
        small = _session_with_row(
            {
                "dimension": "product",
                "label": "Widget",
                "current_revenue": 1050.0,
                "previous_revenue": 1000.0,
                "mom_pct": 0.05,
            }
        )
        c_small = fetch_mom_change_candidate(small, tenant_id=1)
        assert c_small is not None
        assert 0.40 <= c_small.confidence <= 0.95

        # Huge swing → capped at 0.95.
        huge = _session_with_row(
            {
                "dimension": "site",
                "label": "Cairo Downtown",
                "current_revenue": 50000.0,
                "previous_revenue": 1000.0,
                "mom_pct": 49.0,
            }
        )
        c_huge = fetch_mom_change_candidate(huge, tenant_id=1)
        assert c_huge is not None
        assert c_huge.confidence == pytest.approx(0.95)
        # Bigger swing gives higher confidence than small swing.
        assert c_huge.confidence >= c_small.confidence

    def test_query_is_tenant_scoped(self):
        session = _session_with_row(None)
        fetch_mom_change_candidate(session, tenant_id=42)
        assert session.execute.call_count == 1
        args = session.execute.call_args.args
        params = args[1]
        assert params.get("tenant_id") == 42

    def test_exception_returns_none(self):
        """A database error must degrade silently, not poison the pipeline."""
        session = _session_that_raises(RuntimeError("connection lost"))
        assert fetch_mom_change_candidate(session, tenant_id=1) is None

    def test_mom_pct_null_returns_none(self):
        """If the SQL computed NULL for mom_pct (typically previous=0),
        do not emit a candidate."""
        session = _session_with_row(
            {
                "dimension": "product",
                "label": "NewProduct",
                "current_revenue": 1000.0,
                "previous_revenue": 0.0,
                "mom_pct": None,
            }
        )
        assert fetch_mom_change_candidate(session, tenant_id=1) is None
