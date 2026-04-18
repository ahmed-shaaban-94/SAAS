"""Tests for `fetch_expiry_risk_candidate` — Phase 2 follow-up #3 / #402.

The fetcher queries `public_marts.feat_expiry_alerts` for the single
most-at-risk SKU (earliest days_to_expiry, ties broken by biggest
current_quantity) and returns one `InsightCandidate` or None.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.insights_first.models import InsightCandidate
from datapulse.insights_first.repository import fetch_expiry_risk_candidate


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
class TestFetchExpiryRiskCandidate:
    def test_returns_none_when_no_batches_near_expiry(self):
        session = _session_with_row(None)
        assert fetch_expiry_risk_candidate(session, tenant_id=1) is None

    def test_returns_candidate_when_sku_within_30_days(self):
        session = _session_with_row(
            {
                "drug_name": "Paracetamol 500mg Tab",
                "batch_number": "B2026-42",
                "site_code": "S01",
                "current_quantity": 240.0,
                "days_to_expiry": 12,
                "alert_level": "warning",
            }
        )
        c = fetch_expiry_risk_candidate(session, tenant_id=1)
        assert isinstance(c, InsightCandidate)
        assert c.kind == "expiry_risk"
        assert "Paracetamol" in c.title
        assert "12" in c.title or "12 days" in c.body

    def test_candidate_links_to_expiry_page(self):
        session = _session_with_row(
            {
                "drug_name": "Amoxicillin",
                "batch_number": "B-X",
                "site_code": "S02",
                "current_quantity": 50.0,
                "days_to_expiry": 5,
                "alert_level": "critical",
            }
        )
        c = fetch_expiry_risk_candidate(session, tenant_id=1)
        assert c is not None
        assert c.action_href.startswith("/expiry")

    def test_expired_alert_increases_confidence(self):
        """days_to_expiry <= 0 = already past expiry → max confidence."""
        session = _session_with_row(
            {
                "drug_name": "Metformin",
                "batch_number": "B-Y",
                "site_code": "S03",
                "current_quantity": 200.0,
                "days_to_expiry": 0,
                "alert_level": "expired",
            }
        )
        c = fetch_expiry_risk_candidate(session, tenant_id=1)
        assert c is not None
        assert c.confidence >= 0.90

    def test_further_out_means_lower_confidence(self):
        critical = _session_with_row(
            {
                "drug_name": "D1",
                "batch_number": "B1",
                "site_code": "S01",
                "current_quantity": 100.0,
                "days_to_expiry": 3,
                "alert_level": "critical",
            }
        )
        soon = _session_with_row(
            {
                "drug_name": "D2",
                "batch_number": "B2",
                "site_code": "S01",
                "current_quantity": 100.0,
                "days_to_expiry": 28,
                "alert_level": "warning",
            }
        )
        c_crit = fetch_expiry_risk_candidate(critical, tenant_id=1)
        c_soon = fetch_expiry_risk_candidate(soon, tenant_id=1)
        assert c_crit is not None and c_soon is not None
        assert c_crit.confidence >= c_soon.confidence
        # Both floor at 0.40 at least.
        assert c_crit.confidence >= 0.40
        assert c_soon.confidence >= 0.40
        # Both cap at 0.95.
        assert c_crit.confidence <= 0.95

    def test_confidence_clamps_to_unit_interval(self):
        session = _session_with_row(
            {
                "drug_name": "D",
                "batch_number": "B",
                "site_code": "S",
                "current_quantity": 999999.0,
                "days_to_expiry": -50,
                "alert_level": "expired",
            }
        )
        c = fetch_expiry_risk_candidate(session, tenant_id=1)
        assert c is not None
        assert 0.0 <= c.confidence <= 1.0

    def test_query_is_tenant_scoped(self):
        session = _session_with_row(None)
        fetch_expiry_risk_candidate(session, tenant_id=77)
        assert session.execute.call_count == 1
        params = session.execute.call_args.args[1]
        assert params.get("tenant_id") == 77

    def test_query_filters_to_30_day_window(self):
        session = _session_with_row(None)
        fetch_expiry_risk_candidate(session, tenant_id=1)
        sql = str(session.execute.call_args.args[0])
        # Default window is 30 days — enforce it lives in the query.
        assert ":days_threshold" in sql or "days_to_expiry" in sql
        params = session.execute.call_args.args[1]
        if ":days_threshold" in sql:
            assert params.get("days_threshold") == 30

    def test_exception_returns_none(self):
        session = _session_that_raises(RuntimeError("boom"))
        assert fetch_expiry_risk_candidate(session, tenant_id=1) is None

    def test_zero_quantity_returns_none(self):
        """Rows with no stock on hand are not actionable — skip them."""
        session = _session_with_row(
            {
                "drug_name": "Ghost",
                "batch_number": "B",
                "site_code": "S",
                "current_quantity": 0.0,
                "days_to_expiry": 5,
                "alert_level": "critical",
            }
        )
        assert fetch_expiry_risk_candidate(session, tenant_id=1) is None
