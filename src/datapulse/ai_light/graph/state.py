"""Shared state TypedDict for the AI-Light LangGraph.

Design notes:
- No add_messages reducer — this is not a chatbot.
- step_trace uses a custom append reducer to accumulate node-execution records
  without overwriting previous steps.
- All keys are optional (total=False) so nodes can write partial updates cleanly.
"""

from __future__ import annotations

from typing import Any


def _append(existing: list | None, new: list) -> list:
    """Reducer: append new items to an existing list; never replace."""
    base = existing or []
    return base + new


# Alias used by tests
_append_reducer = _append


class AILightState(dict):
    """LangGraph state for the AI-Light insight graph.

    Implemented as a plain dict subclass so LangGraph's TypedDict-based
    reducers work correctly.  Keys are documented below:

    Identity & routing
    ------------------
    tenant_id       str  — from JWT claims
    user_claims     dict — full JWT payload
    run_id          str  — UUID4 as string; generated at request time

    Request
    -------
    insight_type    str  — "summary" | "anomalies" | "changes" | "deep_dive"
    target_date     str | None
    start_date      str | None
    end_date        str | None
    params_hash     str  — MD5 of sorted JSON input params
    require_review  bool — True → interrupt_before=["synthesize"]

    Fetched data (filled by fetch_data / tool calls)
    -------------------------------------------------
    kpi_data             dict | None
    daily_trend          dict | None
    monthly_trend        dict | None
    top_products         dict | None
    top_customers        dict | None
    anomaly_alerts       list | None
    forecast_summary     dict | None
    target_vs_actual     dict | None

    Analysis
    --------
    statistical_analysis dict | None
    llm_raw_output       str  | None
    llm_parsed_output    dict | None

    Outputs (written by synthesize or fallback)
    -------------------------------------------
    narrative        str | None
    highlights       list[str] | None
    anomalies_list   list | None
    deltas           list | None
    degraded         bool

    Cost & observability
    --------------------
    token_usage   dict  — {input, output, total}
    cost_cents    float
    model_used    str
    step_trace    list  — append-only; each entry: {node, ts, status, ...}
    errors        list[str]

    Control
    -------
    validation_retries        int
    circuit_breaker_failures  int
    cache_hit                 bool
    """

    # Registry of keys that use an append reducer instead of replace.
    _APPEND_KEYS: frozenset[str] = frozenset({"step_trace", "errors"})

    def update(self, other: dict[str, Any] | None = None, **kwargs: Any) -> None:  # type: ignore[override]
        """Override update to apply append-reducers for accumulator keys."""
        combined: dict[str, Any] = {}
        if other:
            combined.update(other)
        combined.update(kwargs)
        for key, value in combined.items():
            if key in self._APPEND_KEYS and isinstance(value, list):
                existing = self.get(key, [])
                super().__setitem__(key, existing + value)
            else:
                super().__setitem__(key, value)
