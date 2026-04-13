"""Integration tests — full AI-Light LangGraph with mocked LLM and mocked analytics repo.

Uses real LangGraph (StateGraph + MemorySaver) but mocks:
- langchain_openai.ChatOpenAI → fake LLM returning canned JSON
- cache_get / cache_set → in-memory no-op
- write_invocation_row → no-op (DB not available in unit tests)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("langgraph", reason="langgraph not installed; skip integration tests")

from datapulse.ai_light.graph.state import AILightState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


VALID_SUMMARY_JSON = json.dumps({
    "narrative": "Sales performance was robust with strong YoY growth.",
    "highlights": ["YoY +12%", "Top product drove 40% of revenue", "95 daily customers"],
})


def _make_fake_llm(content: str = VALID_SUMMARY_JSON) -> MagicMock:
    """Return a MagicMock that mimics langchain ChatOpenAI.invoke()."""
    llm = MagicMock()
    response = MagicMock()
    response.content = content
    response.usage_metadata = MagicMock(input_tokens=200, output_tokens=80, total_tokens=280)
    llm.invoke.return_value = response
    llm.model_name = "openai/gpt-4o-mini"
    return llm


def _make_fake_repo() -> MagicMock:
    kpi = MagicMock()
    kpi.model_dump.return_value = {
        "today_gross": 150000.0, "mtd_gross": 3000000.0, "ytd_gross": 12000000.0,
        "mom_growth_pct": 5.2, "yoy_growth_pct": 11.0,
        "daily_transactions": 120, "daily_customers": 95,
    }
    trend = MagicMock()
    trend.model_dump.return_value = {
        "points": [], "total": 0, "average": 0, "minimum": 0, "maximum": 0
    }
    ranking = MagicMock()
    ranking.model_dump.return_value = {
        "items": [{"rank": 1, "name": "Drug A", "value": 50000.0, "pct_of_total": 33.3}],
        "total": 50000.0,
    }
    repo = MagicMock()
    repo.get_kpi_summary.return_value = kpi
    repo.get_daily_trend.return_value = trend
    repo.get_monthly_trend.return_value = trend
    repo.get_top_products.return_value = ranking
    repo.get_top_customers.return_value = ranking
    return repo


def _run_graph(
    insight_type: str = "summary",
    llm_content: str = VALID_SUMMARY_JSON,
    cache_value=None,
) -> dict:
    """Run the full graph with injected fakes and return the final state."""
    # Reset the module-level graph cache between tests
    import datapulse.ai_light.graph.builder as _builder
    from datapulse.ai_light.graph.builder import build_graph, set_runtime_context
    from datapulse.ai_light.graph.tools import build_tool_registry
    from datapulse.config import Settings
    _builder._compiled_graph = None

    repo = _make_fake_repo()
    llm = _make_fake_llm(llm_content)
    tools = build_tool_registry(repo)
    session = MagicMock()

    settings = MagicMock(spec=Settings)
    settings.openrouter_api_key = "test-key"
    settings.openrouter_model = "openrouter/free"
    settings.openrouter_agent_model = "openai/gpt-4o-mini"

    initial_state: AILightState = {
        "tenant_id": "1",
        "run_id": "integration-test-run",
        "insight_type": insight_type,
        "target_date": "2026-04-12",
        "params_hash": "integration_hash",
        "cache_hit": False,
        "validation_retries": 0,
        "circuit_breaker_failures": 0,
        "degraded": False,
        "step_trace": [],
        "cost_cents": 0.0,
    }

    thread_config = {"configurable": {"thread_id": "1:summary:integration-test-run"}}

    with patch("datapulse.ai_light.graph.nodes.cache_get", return_value=cache_value), \
         patch("datapulse.ai_light.graph.nodes.cache_set"), \
         patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v0"), \
         patch("datapulse.ai_light.graph.cost.write_invocation_row"):

        set_runtime_context(llm=llm, tools=tools, session=session)
        graph = build_graph(settings)
        final_state = graph.invoke(initial_state, config=thread_config)

    return final_state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullGraphSummaryPath:
    def test_happy_path_returns_narrative(self):
        state = _run_graph()
        assert state.get("narrative") is not None
        assert "robust" in state["narrative"]

    def test_happy_path_not_degraded(self):
        state = _run_graph()
        assert state.get("degraded") is False

    def test_highlights_list(self):
        state = _run_graph()
        highlights = state.get("highlights", [])
        assert len(highlights) >= 1

    def test_step_trace_records_nodes(self):
        state = _run_graph()
        node_names = {entry["node"] for entry in state["step_trace"]}
        # Must have visited at least these key nodes
        assert "cache_check" in node_names
        assert "synthesize" in node_names

    def test_cache_hit_short_circuits(self):
        """When cache_get returns a cached result, graph should end early."""
        cached = {"narrative": "From cache", "highlights": ["cached highlight"], "degraded": False}
        state = _run_graph(cache_value=cached)

        assert state.get("narrative") == "From cache"
        assert state.get("cache_hit") is True
        # synthesize should NOT have run
        node_names = {entry["node"] for entry in state["step_trace"]}
        assert "synthesize" not in node_names


class TestFallbackOnBadLLMOutput:
    def test_invalid_json_falls_back_after_retries(self):
        """LLM returning invalid JSON twice triggers fallback with degraded=True."""
        state = _run_graph(llm_content="This is not JSON, I tell you.")
        assert state.get("degraded") is True
        assert state.get("narrative") is not None

    def test_fallback_narrative_not_empty(self):
        state = _run_graph(llm_content="gibberish")
        assert len(state.get("narrative", "")) > 0


class TestCircuitBreaker:
    def test_circuit_open_triggers_fallback(self):
        """circuit_breaker_failures >= 3 should route directly to fallback."""
        import datapulse.ai_light.graph.builder as _builder
        from datapulse.ai_light.graph.builder import build_graph, set_runtime_context
        from datapulse.ai_light.graph.tools import build_tool_registry
        from datapulse.config import Settings

        _builder._compiled_graph = None

        repo = _make_fake_repo()
        llm = _make_fake_llm()
        tools = build_tool_registry(repo)
        session = MagicMock()

        settings = MagicMock(spec=Settings)
        settings.openrouter_api_key = "test-key"

        initial_state: AILightState = {
            "tenant_id": "1",
            "run_id": "cb-test-run",
            "insight_type": "summary",
            "target_date": "2026-04-12",
            "params_hash": "cb_hash",
            "cache_hit": False,
            "validation_retries": 0,
            "circuit_breaker_failures": 3,  # circuit open
            "degraded": False,
            "step_trace": [],
            "cost_cents": 0.0,
        }
        thread_config = {"configurable": {"thread_id": "1:summary:cb-test-run"}}

        with patch("datapulse.ai_light.graph.nodes.cache_get", return_value=None), \
             patch("datapulse.ai_light.graph.nodes.cache_set"), \
             patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v0"), \
             patch("datapulse.ai_light.graph.cost.write_invocation_row"):

            set_runtime_context(llm=llm, tools=tools, session=session)
            graph = build_graph(settings)
            final_state = graph.invoke(initial_state, config=thread_config)

        assert final_state.get("degraded") is True
        node_names = {e["node"] for e in final_state["step_trace"]}
        assert "fallback" in node_names
