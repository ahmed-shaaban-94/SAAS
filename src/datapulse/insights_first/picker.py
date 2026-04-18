"""Pure picker — priority-based selection among insight candidates.

No side effects, no I/O. Easy to test, easy to extend.
"""

from __future__ import annotations

from collections.abc import Sequence

from datapulse.insights_first.models import FirstInsight, InsightCandidate

# Priority order — first non-empty kind wins. Unknown kinds are ignored.
_PRIORITY: tuple[str, ...] = (
    "mom_change",
    "expiry_risk",
    "stock_risk",
    "top_seller",
)


def pick_best(
    candidates: Sequence[InsightCandidate | None],
) -> FirstInsight | None:
    """Return the single best `FirstInsight` among *candidates*, or None.

    Selection rule: for each `kind` in the priority tuple (in order),
    return the first candidate in input order with that kind. This makes
    the priority deterministic and order-preserving within a kind.
    """
    non_empty = [c for c in candidates if c is not None]
    if not non_empty:
        return None

    for kind in _PRIORITY:
        for candidate in non_empty:
            if candidate.kind == kind:
                return FirstInsight(
                    kind=candidate.kind,  # type: ignore[arg-type]
                    title=candidate.title,
                    body=candidate.body,
                    action_href=candidate.action_href,
                    confidence=candidate.confidence,
                )
    # No candidate matched any known priority — don't guess.
    return None
