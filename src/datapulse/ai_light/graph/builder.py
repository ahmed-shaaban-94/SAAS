"""LangGraph StateGraph builder for the AI-Light graph.

build_graph(settings) returns a CompiledGraph compiled once at startup.
The compiled graph is cached at module level — it is stateless and thread-safe.
"""

from __future__ import annotations

import threading
from typing import Any

from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)

_compiled_graph: Any = None  # module-level cache


def build_graph(settings: Settings) -> Any:
    """Return the compiled AI-Light StateGraph.

    Lazy-imports LangGraph so the module remains importable without the [ai]
    optional dependency installed.

    The graph is compiled once (MemorySaver checkpointer for Phase A-C) and
    cached at module level for the application lifetime.
    """
    global _compiled_graph  # noqa: PLW0603
    if _compiled_graph is not None:
        return _compiled_graph

    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    from datapulse.ai_light.graph.edges import (
        circuit_breaker_check,
        route_by_type,
        validate_or_retry,
    )
    from datapulse.ai_light.graph.nodes import (
        cache_check,
        cache_write,
        fallback,
        plan_summary,
        synthesize,
        validate,
    )
    from datapulse.ai_light.graph.state import AILightState

    # Node wrappers that close over runtime dependencies (llm, tools, session)
    # are injected at invocation time via the graph config/store mechanism.
    # For Phase A-2 we pass them via the state itself (tools & session via
    # a runtime-injection wrapper pattern).

    graph = StateGraph(AILightState)

    # --- Add all nodes ---
    graph.add_node("cache_check", cache_check)
    graph.add_node("route", _route_passthrough)
    graph.add_node("plan_summary", plan_summary)
    graph.add_node("fetch_data_gate", _fetch_data_gate)
    graph.add_node("fetch_data", _fetch_data_passthrough)
    graph.add_node("analyze", _analyze_passthrough)
    graph.add_node("validate", validate)
    graph.add_node("synthesize", synthesize)
    graph.add_node("fallback", fallback)
    graph.add_node("cost_track", _cost_track_passthrough)
    graph.add_node("cache_write", cache_write)

    # --- Edges ---
    graph.add_edge(START, "cache_check")

    # cache_check → END (hit) or route (miss)
    graph.add_conditional_edges(
        "cache_check",
        lambda s: "end" if s.get("cache_hit") else "route",
        {"end": END, "route": "route"},
    )

    # route → plan_summary (only summary in Phase A-2)
    graph.add_conditional_edges(
        "route",
        route_by_type,
        {"plan_summary": "plan_summary"},
    )

    graph.add_edge("plan_summary", "fetch_data_gate")

    # fetch_data_gate: circuit breaker
    graph.add_conditional_edges(
        "fetch_data_gate",
        circuit_breaker_check,
        {"fetch_data": "fetch_data", "fallback": "fallback"},
    )

    graph.add_edge("fetch_data", "analyze")
    graph.add_edge("analyze", "validate")

    # validate → retry analyze, synthesize, or fallback
    graph.add_conditional_edges(
        "validate",
        validate_or_retry,
        {"analyze": "analyze", "synthesize": "synthesize", "fallback": "fallback"},
    )

    graph.add_edge("synthesize", "cost_track")
    graph.add_edge("fallback", "cost_track")
    graph.add_edge("cost_track", "cache_write")
    graph.add_edge("cache_write", END)

    checkpointer = MemorySaver()
    _compiled_graph = graph.compile(checkpointer=checkpointer)
    log.info("ai_light_graph_compiled")
    return _compiled_graph


# ---------------------------------------------------------------------------
# Runtime-injection passthrough nodes
#
# LangGraph nodes are plain callables(state) -> dict.  Dependencies (LLM,
# tools, DB session) are injected via a thread-local context set by
# AILightGraphService before invoking the graph.
# ---------------------------------------------------------------------------

_local = threading.local()


def set_runtime_context(llm: Any, tools: list[Any], session: Any) -> None:
    """Store per-request dependencies in thread-local storage."""
    _local.llm = llm
    _local.tools = tools
    _local.session = session


def _route_passthrough(state: Any) -> dict[str, Any]:
    """Passthrough node — routing is handled via conditional edges."""
    return {}


def _fetch_data_gate(state: Any) -> dict[str, Any]:
    """Passthrough node for circuit_breaker_check conditional edge."""
    return {}


def _fetch_data_passthrough(state: Any) -> dict[str, Any]:
    from datapulse.ai_light.graph.nodes import fetch_data

    tools = getattr(_local, "tools", [])
    return fetch_data(state, tools)


def _analyze_passthrough(state: Any) -> dict[str, Any]:
    from datapulse.ai_light.graph.nodes import analyze

    llm = getattr(_local, "llm", None)
    if llm is None:
        return {
            "errors": (list(state.get("errors") or []) + ["llm_not_configured"]),
            "step_trace": [{"node": "analyze", "error": "llm_not_configured"}],
        }
    return analyze(state, llm)


def _cost_track_passthrough(state: Any) -> dict[str, Any]:
    from datapulse.ai_light.graph.nodes import cost_track

    session = getattr(_local, "session", None)
    if session is None:
        return {}
    return cost_track(state, session)
