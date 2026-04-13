"""LangGraph node functions for AI-Light.

Each node receives the current ``AILightState`` and returns a *partial* state
dict — LangGraph merges it into the shared state using each field's reducer.

Node inventory (§5 of the plan)
---------------------------------
``cache_check``   — Redis lookup; if hit, populates outputs and sets ``cache_hit=True``.
``route``         — Conditional routing node (returns no state — only drives edges).
``plan_summary``  — Build the data-fetch plan for the summary insight type.
``plan_anomalies``— Build the data-fetch plan for the anomalies insight type.
``plan_changes``  — Build the data-fetch plan for the changes insight type.
``plan_deep_dive``— ReAct tool-use loop: LLM decides which tools to call.
``fetch_data``    — Execute the plan (deterministic for 3 legacy types; ReAct for deep_dive).
``analyze``       — Statistical analysis + single LLM call for narrative generation.
``validate``      — Pydantic schema check; sets ``validation_retries`` for retry edge.
``fallback``      — Stats-only narrative when LLM fails all retries.
``synthesize``    — Compose the final response from validated LLM output.
``cost_track``    — Insert a row into ``public.ai_invocations`` (side-effect node).
``cache_write``   — Write result to Redis with TTL (side-effect node).

Implementation note (Phase A-1): all node functions are stubs that raise
``NotImplementedError``.  Phase A will implement ``cache_check``, ``route``,
``plan_summary``, ``fetch_data``, ``analyze``, ``validate``, ``synthesize``,
``cost_track``, and ``cache_write`` for the summary path.
"""

from __future__ import annotations

from typing import Any


def cache_check(state: dict[str, Any]) -> dict[str, Any]:
    """Check Redis for a cached response matching the current request params."""
    raise NotImplementedError("cache_check — Phase A")


def route(state: dict[str, Any]) -> str:  # noqa: ARG001
    """Return the name of the next node based on ``state['insight_type']``."""
    raise NotImplementedError("route — Phase A")


def plan_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Build the data-fetch plan for summary: KPIs + top products + top customers."""
    raise NotImplementedError("plan_summary — Phase A")


def plan_anomalies(state: dict[str, Any]) -> dict[str, Any]:
    """Build the data-fetch plan for anomalies: daily trend + active alerts."""
    raise NotImplementedError("plan_anomalies — Phase B")


def plan_changes(state: dict[str, Any]) -> dict[str, Any]:
    """Build the data-fetch plan for changes: KPIs for both periods + top movers."""
    raise NotImplementedError("plan_changes — Phase B")


def plan_deep_dive(state: dict[str, Any]) -> dict[str, Any]:
    """ReAct tool-use loop: LLM decides which of the 15 tools to call (max 5 iters)."""
    raise NotImplementedError("plan_deep_dive — Phase C")


def fetch_data(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the tool calls specified by the plan node."""
    raise NotImplementedError("fetch_data — Phase A")


def analyze(state: dict[str, Any]) -> dict[str, Any]:
    """Run statistical analysis and a single LLM call to produce the narrative."""
    raise NotImplementedError("analyze — Phase A")


def validate(state: dict[str, Any]) -> dict[str, Any]:
    """Validate ``llm_parsed_output`` against the insight-type Pydantic schema."""
    raise NotImplementedError("validate — Phase A")


def fallback(state: dict[str, Any]) -> dict[str, Any]:
    """Produce a stats-only narrative when all LLM retries are exhausted."""
    raise NotImplementedError("fallback — Phase A")


def synthesize(state: dict[str, Any]) -> dict[str, Any]:
    """Compose the final API response from validated LLM output + statistical analysis."""
    raise NotImplementedError("synthesize — Phase A")


def cost_track(state: dict[str, Any]) -> dict[str, Any]:
    """Insert a row into ``public.ai_invocations`` for cost monitoring."""
    raise NotImplementedError("cost_track — Phase A")


def cache_write(state: dict[str, Any]) -> dict[str, Any]:
    """Write the final response to Redis with an insight-type-specific TTL."""
    raise NotImplementedError("cache_write — Phase A")
