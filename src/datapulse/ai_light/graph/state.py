"""AILightState — the single TypedDict flowing through the LangGraph."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from typing_extensions import TypedDict


def _append(left: list | None, right: list | None) -> list:
    """Custom reducer: append step_trace records across nodes."""
    return (left or []) + (right or [])


# Alias used by tests
_append_reducer = _append


class AILightState(TypedDict, total=False):
    """State schema for the AI Light LangGraph.

    ``total=False`` means every key is optional — nodes return only the keys
    they produce; LangGraph merges them into the running state.
    ``step_trace`` uses a custom append reducer so every node can record its
    execution without overwriting earlier records.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    tenant_id: str
    run_id: str

    # ── Request ───────────────────────────────────────────────────────────
    insight_type: str  # summary | anomalies | changes | deep_dive
    target_date: date | None
    start_date: date | None
    end_date: date | None
    current_date: date | None
    previous_date: date | None
    params_hash: str

    # ── Fetched data ───────────────────────────────────────────────────────
    kpi_data: dict[str, Any] | None
    kpi_current: dict[str, Any] | None
    kpi_previous: dict[str, Any] | None
    daily_trend: dict[str, Any] | None
    top_products: dict[str, Any] | None
    top_customers: dict[str, Any] | None
    top_staff: dict[str, Any] | None
    site_performance: dict[str, Any] | None
    anomaly_alerts: list[dict[str, Any]] | None
    top_gainers: dict[str, Any] | None
    top_losers: dict[str, Any] | None

    # ── LLM analysis ──────────────────────────────────────────────────────
    statistical_analysis: dict[str, Any] | None
    llm_raw_output: str | None
    llm_parsed_output: dict[str, Any] | None
    token_usage: dict[str, int] | None
    model_used: str | None

    # ── Outputs ───────────────────────────────────────────────────────────
    narrative: str | None
    highlights: list[str] | None
    anomalies_list: list[dict[str, Any]] | None
    deltas: list[dict[str, Any]] | None
    degraded: bool

    # ── Cost / observability ──────────────────────────────────────────────
    cost_cents: float | None
    step_trace: Annotated[list[dict[str, Any]], _append]
    errors: list[str] | None

    # ── Control ───────────────────────────────────────────────────────────
    validation_retries: int
    circuit_breaker_failures: int
    cache_hit: bool
