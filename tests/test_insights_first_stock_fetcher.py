"""Tests for `fetch_stock_risk_candidate` — Phase 2 follow-up #4 / #402.

Picks the SKU with the biggest deficit below its reorder point.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.insights_first.models import InsightCandidate
from datapulse.insights_first.repository import fetch_stock_risk_candidate


def _session_with_row(row: dict | None) -> MagicMock:
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
class TestFetchStockRiskCandidate:
    def test_returns_none_when_no_deficit_rows(self):
        session = _session_with_row(None)
        assert fetch_stock_risk_candidate(session, tenant_id=1) is None

    def test_returns_candidate_for_biggest_deficit(self):
        session = _session_with_row(
            {
                "drug_name": "Paracetamol 500mg Tab",
                "drug_code": "P500",
                "site_code": "S01",
                "current_quantity": 20.0,
                "reorder_point": 100.0,
                "reorder_quantity": 200.0,
            }
        )
        c = fetch_stock_risk_candidate(session, tenant_id=1)
        assert isinstance(c, InsightCandidate)
        assert c.kind == "stock_risk"
        assert "Paracetamol" in c.title
        # Title should communicate the shortage size or the relative gap.
        assert "80" in c.title or "80" in c.body or "reorder" in c.body.lower()

    def test_candidate_links_to_inventory_page(self):
        session = _session_with_row(
            {
                "drug_name": "Amoxicillin",
                "drug_code": "AMOX",
                "site_code": "S02",
                "current_quantity": 5.0,
                "reorder_point": 50.0,
                "reorder_quantity": 100.0,
            }
        )
        c = fetch_stock_risk_candidate(session, tenant_id=1)
        assert c is not None
        assert c.action_href.startswith("/inventory")

    def test_zero_on_hand_surfaces_as_stockout(self):
        """current_quantity == 0 is the worst case; body should say 'out of stock'."""
        session = _session_with_row(
            {
                "drug_name": "Insulin",
                "drug_code": "INS",
                "site_code": "S03",
                "current_quantity": 0.0,
                "reorder_point": 20.0,
                "reorder_quantity": 50.0,
            }
        )
        c = fetch_stock_risk_candidate(session, tenant_id=1)
        assert c is not None
        assert (
            "out of stock" in c.body.lower()
            or "stockout" in c.body.lower()
            or "out" in c.body.lower()
        )

    def test_deeper_deficit_yields_higher_confidence(self):
        shallow = _session_with_row(
            {
                "drug_name": "D1",
                "drug_code": "D1",
                "site_code": "S01",
                "current_quantity": 95.0,
                "reorder_point": 100.0,
                "reorder_quantity": 200.0,
            }
        )
        deep = _session_with_row(
            {
                "drug_name": "D2",
                "drug_code": "D2",
                "site_code": "S01",
                "current_quantity": 5.0,
                "reorder_point": 100.0,
                "reorder_quantity": 200.0,
            }
        )
        c_shallow = fetch_stock_risk_candidate(shallow, tenant_id=1)
        c_deep = fetch_stock_risk_candidate(deep, tenant_id=1)
        assert c_shallow is not None and c_deep is not None
        assert c_deep.confidence >= c_shallow.confidence
        # Both within unit interval.
        assert 0.40 <= c_shallow.confidence <= 0.95
        assert 0.40 <= c_deep.confidence <= 0.95

    def test_confidence_clamps_to_unit_interval(self):
        session = _session_with_row(
            {
                "drug_name": "D",
                "drug_code": "D",
                "site_code": "S",
                "current_quantity": 0.0,
                "reorder_point": 9999.0,
                "reorder_quantity": 20000.0,
            }
        )
        c = fetch_stock_risk_candidate(session, tenant_id=1)
        assert c is not None
        assert 0.0 <= c.confidence <= 1.0

    def test_query_is_tenant_scoped(self):
        session = _session_with_row(None)
        fetch_stock_risk_candidate(session, tenant_id=99)
        assert session.execute.call_count == 1
        params = session.execute.call_args.args[1]
        assert params.get("tenant_id") == 99

    def test_exception_returns_none(self):
        session = _session_that_raises(RuntimeError("connection lost"))
        assert fetch_stock_risk_candidate(session, tenant_id=1) is None

    def test_current_quantity_above_reorder_returns_none(self):
        """Defensive: if the query somehow returns a row with current > reorder
        (shouldn't happen given the WHERE clause), the fetcher refuses."""
        session = _session_with_row(
            {
                "drug_name": "PlentyStock",
                "drug_code": "P",
                "site_code": "S",
                "current_quantity": 500.0,
                "reorder_point": 100.0,
                "reorder_quantity": 200.0,
            }
        )
        assert fetch_stock_risk_candidate(session, tenant_id=1) is None

    def test_null_reorder_point_returns_none(self):
        session = _session_with_row(
            {
                "drug_name": "D",
                "drug_code": "D",
                "site_code": "S",
                "current_quantity": 10.0,
                "reorder_point": None,
                "reorder_quantity": None,
            }
        )
        assert fetch_stock_risk_candidate(session, tenant_id=1) is None
