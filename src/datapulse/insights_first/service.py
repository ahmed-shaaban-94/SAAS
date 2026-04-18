"""Orchestrates the fetchers and delegates to the pure picker.

Each fetcher is a callable ``(tenant_id: int) -> InsightCandidate | None``.
Fetchers are isolated: an exception in one does not prevent the others
from running. This is intentional — a degraded insight is better than a
missing insight on a user's first dashboard view.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from datapulse.insights_first.models import FirstInsight, InsightCandidate
from datapulse.insights_first.picker import pick_best
from datapulse.logging import get_logger

log = get_logger(__name__)

Fetcher = Callable[[int], InsightCandidate | None]


class FirstInsightService:
    """Collects candidates from multiple sources, delegates to the picker."""

    def __init__(self, fetchers: Sequence[Fetcher]) -> None:
        self._fetchers: tuple[Fetcher, ...] = tuple(fetchers)

    def get_first(self, tenant_id: int) -> FirstInsight | None:
        """Return the single highest-priority non-empty insight, or None."""
        candidates: list[InsightCandidate | None] = []
        for fetcher in self._fetchers:
            try:
                candidates.append(fetcher(tenant_id))
            except Exception as exc:  # noqa: BLE001
                # Degrade gracefully — record and move on.
                log.warning(
                    "first_insight_fetcher_failed",
                    fetcher=getattr(fetcher, "__name__", repr(fetcher)),
                    tenant_id=tenant_id,
                    error=str(exc),
                )
                candidates.append(None)

        return pick_best(candidates)
