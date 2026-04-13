"""LangGraph conditional edge functions for AI-Light.

Conditional edges read ``AILightState`` and return the *name* of the next node
(a string).  LangGraph's ``add_conditional_edges`` maps that string to the
actual node function.

Edge functions
--------------
``route_by_type``         — After ``route`` node: dispatches to type-specific plan node.
``validate_or_retry``     — After ``validate`` node: retries ``analyze`` (max 2) or proceeds.
``circuit_breaker_check`` — After ``fetch_data``: short-circuits to ``fallback`` if CB open.
``cache_or_continue``     — After ``cache_check``: exits graph on cache hit, continues on miss.

Implementation note (Phase A-1): stubs only.  Phase A will implement
``route_by_type``, ``validate_or_retry``, and ``cache_or_continue`` for the
summary path.
"""

from __future__ import annotations

from typing import Any


def route_by_type(state: dict[str, Any]) -> str:
    """Map ``insight_type`` to the corresponding plan node name.

    Returns one of: ``"plan_summary"``, ``"plan_anomalies"``,
    ``"plan_changes"``, ``"plan_deep_dive"``.
    """
    raise NotImplementedError("route_by_type — Phase A")


def validate_or_retry(state: dict[str, Any]) -> str:
    """Return ``"analyze"`` for a retry or ``"synthesize"`` / ``"fallback"`` on terminal state.

    Retry logic: if ``validation_retries < 2`` and the last validation failed,
    route back to ``"analyze"`` with an amended prompt.  After 2 retries route
    to ``"fallback"``.  On success route to ``"synthesize"``.
    """
    raise NotImplementedError("validate_or_retry — Phase A")


def circuit_breaker_check(state: dict[str, Any]) -> str:
    """Return ``"analyze"`` normally or ``"fallback"`` when the circuit breaker is open."""
    raise NotImplementedError("circuit_breaker_check — Phase A")


def cache_or_continue(state: dict[str, Any]) -> str:
    """Return ``"__end__"`` on a cache hit or ``"route"`` on a miss."""
    raise NotImplementedError("cache_or_continue — Phase A")
