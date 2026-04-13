"""LangGraph graph builder for AI-Light.

``build_graph`` compiles the state-machine once at application startup.  The
compiled ``CompiledGraph`` object is thread-safe and reused across requests.

Graph topology (§2 of the plan)
---------------------------------
::

    START
      └─► cache_check ──(hit)──► END_CACHED
                      └─(miss)─► route
                                  ├─(summary)──► plan_summary
                                  ├─(anomalies)► plan_anomalies
                                  ├─(changes)──► plan_changes
                                  └─(deep_dive)► plan_deep_dive
                                       └───────────────────► fetch_data
                                                           ├─(cb_open)──► fallback
                                                           └─(ok)───────► analyze
                                                                     └─► validate
                                                                 ├─(retry)─► analyze
                                                                 ├─(fail)──► fallback
                                                                 └─(ok)────► synthesize
                                                            └─► cost_track ─► cache_write ─► END

Phase D adds ``interrupt_before=["synthesize"]`` for human-in-the-loop review.

Implementation note (Phase A-1): ``build_graph`` is a stub.  Phase A will wire
the summary path using ``langgraph.graph.StateGraph``.  The import is guarded
so the ``[ai]`` extras are not required before the flag is enabled.
"""

from __future__ import annotations

from typing import Any


def build_graph(settings: Any) -> Any:  # noqa: ARG001
    """Compile and return the AI-Light LangGraph state-machine.

    Parameters
    ----------
    settings:
        Application ``Settings`` instance (used for checkpoint backend selection
        and LangSmith configuration).

    Returns
    -------
    CompiledGraph
        A LangGraph compiled graph, safe to reuse across threads and requests.

    Raises
    ------
    NotImplementedError
        Until Phase A implements the summary path.
    ImportError
        If ``langgraph`` is not installed (``pip install datapulse[ai]``).
    """
    raise NotImplementedError(
        "build_graph is not yet implemented. "
        "Install the [ai] extras and enable Phase A to use LangGraph."
    )
