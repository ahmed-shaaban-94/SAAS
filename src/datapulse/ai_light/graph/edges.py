"""Conditional edge functions for the AI-Light LangGraph."""

from __future__ import annotations

from datapulse.ai_light.graph.state import AILightState

_MAX_RETRIES = 2
_CIRCUIT_BREAKER_THRESHOLD = 3


def route_by_type(state: AILightState) -> str:
    """Route from *route* node to the appropriate plan node based on insight_type."""
    insight_type = state.get("insight_type", "summary")
    if insight_type == "summary":
        return "plan_summary"
    # Future: anomalies, changes, deep_dive
    return "plan_summary"


def validate_or_retry(state: AILightState) -> str:
    """After validate: retry analyze if retries remain, else synthesize or fallback."""
    retries = state.get("validation_retries", 0)
    parsed = state.get("llm_parsed_output")

    if parsed is not None:
        # Try to validate
        try:
            from datapulse.ai_light.graph.schemas import SummaryOutput

            insight_type = state.get("insight_type", "summary")
            if insight_type == "summary":
                SummaryOutput(**parsed)
                return "synthesize"
        except Exception:
            pass

    # Validation failed
    if retries < _MAX_RETRIES:
        return "analyze"
    return "fallback"


def circuit_breaker_check(state: AILightState) -> str:
    """Check circuit breaker before fetch_data; open circuit goes to fallback."""
    failures = state.get("circuit_breaker_failures", 0)
    if failures >= _CIRCUIT_BREAKER_THRESHOLD:
        return "fallback"
    return "fetch_data"
