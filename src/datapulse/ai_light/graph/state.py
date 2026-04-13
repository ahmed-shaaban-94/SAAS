"""LangGraph state schema for AI-Light.

Defines ``AILightState`` — the single TypedDict that flows through every node in
the graph.  Fields are grouped by lifecycle stage:

* **Identity** — tenant / user / run identifiers (set once at graph entry).
* **Request**  — insight type, date range, params hash, feature flag.
* **Fetched data** — raw DB / service results (populated by ``fetch_data`` node).
* **Analysis** — statistical summaries and raw LLM output.
* **Outputs**  — final response fields returned to the API caller.
* **Cost / observability** — token counts, cost estimate, step trace.
* **Control**  — retry counters, circuit-breaker failures, cache hit flag.

``step_trace`` uses a custom *append* reducer so each node can push a record
without overwriting the full list.  All other keys use LangGraph's default
``last-write-wins`` reducer.

Implementation note (Phase A-1): this file is a scaffold — ``AILightState`` is
declared but the graph is not yet wired.  The LangGraph import is deferred so
the ``[ai]`` extras are not required at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # LangGraph is an optional dependency — only imported for type-checking.
    pass


# ---------------------------------------------------------------------------
# Step-trace append reducer
# ---------------------------------------------------------------------------

def _append_reducer(left: list[Any], right: Any) -> list[Any]:
    """Append *right* (a single record or list) to *left*."""
    if isinstance(right, list):
        return left + right
    return left + [right]


# ---------------------------------------------------------------------------
# AILightState
# ---------------------------------------------------------------------------

# NOTE: Full TypedDict definition lands in Phase A (summary path implementation).
# Declared here as a plain dict alias so imports work before langgraph is installed.
AILightState = dict  # type: ignore[assignment]
