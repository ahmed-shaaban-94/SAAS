"""AILightState — LangGraph state schema for the AI-Light graph."""

from __future__ import annotations

from typing import Annotated, Any

from typing_extensions import TypedDict


def _append_reducer(existing: list | None, new: list | None) -> list:
    """Append new items to existing list; never replace the whole list."""
    base = existing if existing is not None else []
    addition = new if new is not None else []
    return base + addition


class AILightState(TypedDict, total=False):
    """Shared state flowing through the AI-Light LangGraph."""

    # --- Identity ---
    tenant_id: str
    user_claims: dict[str, Any]
    run_id: str  # UUID string

    # --- Request ---
    insight_type: str  # summary | anomalies | changes | deep_dive
    target_date: str | None
    start_date: str | None
    end_date: str | None
    params_hash: str
    use_langgraph: bool

    # --- Fetched data ---
    kpi_data: dict[str, Any] | None
    daily_trend: dict[str, Any] | None
    monthly_trend: dict[str, Any] | None
    top_products: dict[str, Any] | None
    top_customers: dict[str, Any] | None
    anomaly_alerts: list[dict[str, Any]] | None
    forecast_summary: dict[str, Any] | None
    target_vs_actual: dict[str, Any] | None
    churn_predictions: dict[str, Any] | None

    # --- Analysis ---
    statistical_analysis: dict[str, Any] | None
    llm_raw_output: str | None
    llm_parsed_output: dict[str, Any] | None

    # --- Outputs ---
    narrative: str | None
    highlights: list[str] | None
    anomalies_list: list[dict[str, Any]] | None
    deltas: list[dict[str, Any]] | None
    degraded: bool

    # --- Cost / observability ---
    token_usage: dict[str, int] | None  # {input, output, total}
    cost_cents: float
    model_used: str | None
    step_trace: Annotated[list[dict[str, Any]], _append_reducer]
    errors: list[str] | None

    # --- Control ---
    validation_retries: int
    circuit_breaker_failures: int
    cache_hit: bool
