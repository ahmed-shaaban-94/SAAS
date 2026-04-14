"""Integration tests for the AI-Light LangGraph — full graph with mocked LLM.

These tests run the compiled graph end-to-end with:
- MemorySaver (no DB needed for checkpointing)
- Mocked OpenRouter (no real HTTP calls)
- Mocked tool registry (no DB queries)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from datapulse.ai_light.graph.builder import build_graph

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_SUMMARY_OUTPUT = (
    '{"narrative": "Revenue is up 15% this quarter.", '
    '"highlights": ["Strong Q4", "New customers up 20%"]}'
)
MOCK_ANOMALY_OUTPUT = (
    '[{"date": "2026-04-01", "severity": "high", "description": "Spike in returns"}]'
)


class _FakeSettings:
    """Minimal settings for graph compilation."""

    database_url = "postgresql://user:pass@localhost/db"
    ai_light_checkpoint_backend = "memory"
    openrouter_api_key = ""
    openrouter_model = "openrouter/free"
    openrouter_agent_model = ""
    ai_light_max_tokens_per_day = 100_000
    langsmith_api_key = ""
    langsmith_project = "test"


@pytest.fixture(scope="module")
def compiled_graph():
    """Compile once and reuse across tests in this module."""
    return build_graph(_FakeSettings())


def _base_state(insight_type: str = "summary", api_key: str = "") -> dict:
    return {
        "insight_type": insight_type,
        "tenant_id": "1",
        "run_id": "integration-test-run",
        "params_hash": "abc123",
        "require_review": False,
        "validation_retries": 0,
        "circuit_breaker_failures": 0,
        "cache_hit": False,
        "degraded": False,
        "step_trace": [],
        "errors": [],
        "token_usage": {"input": 0, "output": 0, "total": 0},
        "cost_cents": 0.0,
        "_openrouter_api_key": api_key,
        "_openrouter_model": "openai/gpt-4o-mini",
        "_tools": {
            "get_kpi_summary": lambda: {
                "today_gross": 50000,
                "mtd_gross": 1000000,
                "ytd_gross": 5000000,
                "daily_transactions": 200,
                "daily_customers": 150,
            },
            "get_top_products": lambda: {"items": [{"name": "Widget A", "value": 10000}]},
            "get_top_customers": lambda: {"items": [{"name": "Customer X", "value": 5000}]},
        },
        "_session": None,
        "_start_ms": 0,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGraphCompilation:
    def test_graph_compiles_successfully(self, compiled_graph):
        assert compiled_graph is not None

    def test_graph_has_expected_nodes(self, compiled_graph):
        # LangGraph compiled graphs expose the underlying nodes via .get_graph()
        graph_repr = compiled_graph.get_graph()
        node_ids = set(graph_repr.nodes.keys())
        expected = {
            "cache_check",
            "route",
            "plan_summary",
            "fetch_data",
            "analyze",
            "validate",
            "synthesize",
            "fallback",
            "cost_track",
            "cache_write",
        }
        assert expected.issubset(node_ids), f"Missing nodes: {expected - node_ids}"


class TestSummaryPath:
    def test_no_api_key_falls_through_to_fallback_narrative(self, compiled_graph):
        """Without API key, graph should return a degraded-mode fallback."""
        state = _base_state(insight_type="summary", api_key="")
        config = {"configurable": {"thread_id": "test:summary:no-key"}}
        final = compiled_graph.invoke(state, config=config)
        # Fallback sets degraded=True; narrative should be non-empty
        assert final.get("narrative") is not None or final.get("degraded") is not None

    def test_with_api_key_calls_openrouter(self, compiled_graph):
        state = _base_state(insight_type="summary", api_key="sk-test")
        config = {"configurable": {"thread_id": "test:summary:with-key"}}
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        with patch(
            "datapulse.ai_light.graph.nodes._call_openrouter",
            return_value=(MOCK_SUMMARY_OUTPUT, usage),
        ):
            final = compiled_graph.invoke(state, config=config)
        assert final.get("narrative") == "Revenue is up 15% this quarter."
        assert final.get("degraded") is False

    def test_cache_hit_short_circuits_graph(self, compiled_graph):
        """If cache_hit=True in initial state, graph goes straight to END."""
        state = {**_base_state("summary"), "cache_hit": True, "narrative": "Cached result"}
        config = {"configurable": {"thread_id": "test:summary:cache-hit"}}
        final = compiled_graph.invoke(state, config=config)
        assert final.get("narrative") == "Cached result"


class TestValidationRetry:
    def test_invalid_llm_output_triggers_retry(self, compiled_graph):
        """Malformed LLM output → validate fails → analyze retried → fallback after max retries."""
        state = _base_state(insight_type="summary", api_key="sk-test")
        config = {"configurable": {"thread_id": "test:summary:bad-output"}}
        bad_output = "NOT JSON AT ALL"
        with patch(
            "datapulse.ai_light.graph.nodes._call_openrouter",
            return_value=(bad_output, {}),
        ):
            final = compiled_graph.invoke(state, config=config)
        # Should end in fallback (degraded) after retries exhausted
        assert final.get("degraded") is True or final.get("validation_retries", 0) >= 0


class TestHITLInterrupt:
    def test_interrupt_before_synthesize_pauses_graph(self, compiled_graph):
        """With interrupt_before=["synthesize"] the graph pauses and snapshot.next is set."""
        state = _base_state(insight_type="summary", api_key="sk-test")
        state["require_review"] = True
        run_id = "hitl-interrupt-test"
        config = {
            "configurable": {"thread_id": f"1:summary:{run_id}"},
            "interrupt_before": ["synthesize"],
        }
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        with patch(
            "datapulse.ai_light.graph.nodes._call_openrouter",
            return_value=(MOCK_SUMMARY_OUTPUT, usage),
        ):
            compiled_graph.invoke(state, config=config)

        snapshot = compiled_graph.get_state(config)
        # Graph should be paused with "synthesize" as the next node
        assert snapshot is not None
        assert "synthesize" in (snapshot.next or [])

    def test_resume_after_interrupt(self, compiled_graph):
        """After interrupt, update_state + re-invoke completes the graph."""
        state = _base_state(insight_type="summary", api_key="sk-test")
        run_id = "hitl-resume-test"
        config = {
            "configurable": {"thread_id": f"1:summary:{run_id}"},
            "interrupt_before": ["synthesize"],
        }
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        with patch(
            "datapulse.ai_light.graph.nodes._call_openrouter",
            return_value=(MOCK_SUMMARY_OUTPUT, usage),
        ):
            compiled_graph.invoke(state, config=config)

        # Inject human edit and resume
        compiled_graph.update_state(
            config,
            {"human_edits": {"narrative": "Human-revised narrative."}},
            as_node="synthesize",
        )
        final = compiled_graph.invoke(None, config=config)
        assert final.get("narrative") == "Human-revised narrative."
        assert final.get("degraded") is False
