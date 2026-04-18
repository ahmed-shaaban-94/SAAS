"""Pydantic models for the first-insight picker (Phase 2 Task 3 / #402)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InsightKind = Literal[
    "mom_change",
    "expiry_risk",
    "stock_risk",
    "top_seller",
]


class FirstInsight(BaseModel):
    """The single best insight surfaced on a new user's first dashboard view."""

    model_config = ConfigDict(frozen=True)

    kind: InsightKind
    title: str
    body: str
    action_href: str
    confidence: float = Field(ge=0.0, le=1.0)


class FirstInsightResponse(BaseModel):
    """Wraps the optional insight so the client always gets a valid JSON shape,
    even when no insight is available for this tenant yet.
    """

    model_config = ConfigDict(frozen=True)

    insight: FirstInsight | None = None


class InsightCandidate(BaseModel):
    """A candidate surfaced by one of the data-source fetchers.

    The picker chooses among candidates by `kind` priority order, not by
    confidence. Confidence is carried through to the UI for display.
    """

    model_config = ConfigDict(frozen=True)

    # `kind` is intentionally `str` (not `InsightKind`) so future kinds
    # can be added by new fetchers without a schema migration; the picker
    # ignores unknown kinds rather than crashing on them.
    kind: str
    title: str
    body: str
    action_href: str
    confidence: float = Field(ge=0.0, le=1.0)
