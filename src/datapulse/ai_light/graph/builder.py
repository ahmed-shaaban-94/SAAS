"""Graph builder for AI-Light LangGraph orchestration (Phase D: HITL + PostgresSaver).

Call build_graph() once at startup and reuse the compiled graph.  The graph is
stateless; per-request state (tenant session, API keys, run_id) is injected into
the initial state dict before invoking the graph.

Phase D additions:
- When settings.ai_light_checkpoint_backend == "postgres", uses PostgresSaver
  (schema="ai_checkpoints") instead of MemorySaver.
- Compiles with interrupt_before=["synthesize"] when the caller sets
  require_review=True in the initial state.  The graph is compiled ONCE and
  interrupt_before is passed at invoke/stream time, not compile time.

Note on interrupt_before at invoke time:
  LangGraph 0.2+ supports passing interrupt_before to .invoke()/.astream() as a
  runtime override via the config dict:
      config = {"interrupt_before": ["synthesize"]}
  This avoids having to compile two separate graphs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from datapulse.ai_light.graph.edges import (
    cache_or_continue,
    circuit_breaker_check,
    route_by_type,
    validate_or_retry,
)
from datapulse.ai_light.graph.nodes import (
    analyze,
    cache_check,
    cache_write,
    cost_track,
    fallback,
    fetch_data,
    plan_anomalies,
    plan_changes,
    plan_deep_dive,
    plan_summary,
    route,
    synthesize,
    validate,
)

if TYPE_CHECKING:
    from datapulse.core.config import Settings


def _build_checkpointer(settings: Settings):
    """Return the appropriate checkpointer based on configuration.

    Memory:   fast, no persistence — suitable for Phases A–C and testing.
    Postgres: durable, survives restarts — required for Phase D HITL approval flow.
    """
    backend = getattr(settings, "ai_light_checkpoint_backend", "memory")
    if backend == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            conn_string = settings.database_url
            return PostgresSaver.from_conn_string(
                conn_string,
                schema_name="ai_checkpoints",
            )
        except ImportError as exc:
            raise ImportError(
                "langgraph-checkpoint-postgres is required for Postgres checkpointing. "
                "Install it with: pip install langgraph-checkpoint-postgres"
            ) from exc
    else:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()


def build_graph(settings: Settings):
    """Compile the AI-Light StateGraph and return it.

    The returned object is thread-safe and should be cached at module level or
    as a FastAPI startup artifact.

    For HITL runs (require_review=True) pass interrupt_before=["synthesize"]
    in the LangGraph config at invoke/stream time — no separate compilation needed.
    """
    checkpointer = _build_checkpointer(settings)

    graph = StateGraph(dict)

    # --- Nodes ---
    graph.add_node("cache_check", cache_check)
    graph.add_node("route", route)
    graph.add_node("plan_summary", plan_summary)
    graph.add_node("plan_anomalies", plan_anomalies)
    graph.add_node("plan_changes", plan_changes)
    graph.add_node("plan_deep_dive", plan_deep_dive)
    graph.add_node("fetch_data", fetch_data)
    graph.add_node("analyze", analyze)
    graph.add_node("validate", validate)
    graph.add_node("synthesize", synthesize)
    graph.add_node("fallback", fallback)
    graph.add_node("cost_track", cost_track)
    graph.add_node("cache_write", cache_write)

    # --- Edges ---
    graph.add_edge(START, "cache_check")

    # After cache_check: hit → END, miss → route
    graph.add_conditional_edges(
        "cache_check",
        cache_or_continue,
        {
            "__end__": END,
            "route": "route",
        },
    )

    # After route: branch by insight_type
    graph.add_conditional_edges(
        "route",
        route_by_type,
        {
            "plan_summary": "plan_summary",
            "plan_anomalies": "plan_anomalies",
            "plan_changes": "plan_changes",
            "plan_deep_dive": "plan_deep_dive",
        },
    )

    # All plan_* → fetch_data
    for plan_node in ("plan_summary", "plan_anomalies", "plan_changes", "plan_deep_dive"):
        graph.add_edge(plan_node, "fetch_data")

    # fetch_data → analyze OR fallback (circuit breaker)
    graph.add_conditional_edges(
        "fetch_data",
        circuit_breaker_check,
        {
            "analyze": "analyze",
            "fallback": "fallback",
        },
    )

    # analyze → validate
    graph.add_edge("analyze", "validate")

    # validate → synthesize | analyze (retry) | fallback
    graph.add_conditional_edges(
        "validate",
        validate_or_retry,
        {
            "synthesize": "synthesize",
            "analyze": "analyze",
            "fallback": "fallback",
        },
    )

    # synthesize / fallback → cost_track → cache_write → END
    graph.add_edge("synthesize", "cost_track")
    graph.add_edge("fallback", "cost_track")
    graph.add_edge("cost_track", "cache_write")
    graph.add_edge("cache_write", END)

    return graph.compile(checkpointer=checkpointer)
