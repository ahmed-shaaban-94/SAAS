"""Tests for insights_first.service — orchestrates fetchers + picker.

Phase 2 Task 3 / #402.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.insights_first.models import FirstInsight, InsightCandidate
from datapulse.insights_first.service import FirstInsightService


def _candidate(kind: str, confidence: float = 0.5) -> InsightCandidate:
    return InsightCandidate(
        kind=kind,
        title=f"{kind}-title",
        body=f"{kind}-body",
        action_href=f"/{kind}",
        confidence=confidence,
    )


@pytest.mark.unit
class TestFirstInsightService:
    def test_returns_none_when_all_fetchers_return_none(self):
        service = FirstInsightService(
            fetchers=[
                lambda _tid: None,
                lambda _tid: None,
            ],
        )
        assert service.get_first(tenant_id=1) is None

    def test_returns_highest_priority_non_empty_candidate(self):
        service = FirstInsightService(
            fetchers=[
                lambda _tid: _candidate("top_seller", 0.9),
                lambda _tid: _candidate("mom_change", 0.3),
                lambda _tid: _candidate("expiry_risk", 0.5),
            ],
        )
        result = service.get_first(tenant_id=1)
        assert isinstance(result, FirstInsight)
        assert result.kind == "mom_change"

    def test_passes_tenant_id_to_every_fetcher(self):
        fetcher1 = MagicMock(return_value=None)
        fetcher2 = MagicMock(return_value=_candidate("top_seller"))

        service = FirstInsightService(fetchers=[fetcher1, fetcher2])
        service.get_first(tenant_id=42)

        fetcher1.assert_called_once_with(42)
        fetcher2.assert_called_once_with(42)

    def test_isolates_failing_fetchers(self):
        """A misbehaving fetcher must not poison the whole insight pipeline —
        the other fetchers still run and the picker still produces a result."""

        def boom(_tid: int) -> InsightCandidate | None:
            raise RuntimeError("simulated downstream failure")

        service = FirstInsightService(
            fetchers=[
                boom,
                lambda _tid: _candidate("top_seller", 0.8),
            ],
        )
        result = service.get_first(tenant_id=1)
        assert result is not None
        assert result.kind == "top_seller"

    def test_no_fetchers_configured_returns_none(self):
        service = FirstInsightService(fetchers=[])
        assert service.get_first(tenant_id=1) is None
