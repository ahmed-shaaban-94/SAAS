"""Unit tests for AI-Light graph nodes — each node in isolation.

No DB, no LLM.  State is built manually and node output is asserted.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from datapulse.ai_light.graph.nodes import (
    analyze,
    cache_check,
    cost_track,
    fallback,
    fetch_data,
    plan_anomalies,
    plan_changes,
    plan_deep_dive,
    plan_summary,
    synthesize,
    validate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_state(**overrides) -> dict:
    return {
        "tenant_id": "1",
        "run_id": "test-run-id",
        "insight_type": "summary",
        "validation_retries": 0,
        "circuit_breaker_failures": 0,
        "step_trace": [],
        "errors": [],
        "cache_hit": False,
        "degraded": False,
        **overrides,
    }


# ---------------------------------------------------------------------------
# cache_check
# ---------------------------------------------------------------------------


class TestCacheCheck:
    def test_returns_cache_hit_false(self):
        result = cache_check(_base_state())
        assert result["cache_hit"] is False
        assert any(s["node"] == "cache_check" for s in result["step_trace"])


# ---------------------------------------------------------------------------
# plan_* nodes
# ---------------------------------------------------------------------------


class TestPlanNodes:
    def test_plan_summary(self):
        result = plan_summary(_base_state())
        assert "get_kpi_summary" in result["planned_tools"]
        assert "get_top_products" in result["planned_tools"]

    def test_plan_anomalies(self):
        result = plan_anomalies(_base_state(insight_type="anomalies"))
        assert "get_daily_trend" in result["planned_tools"]

    def test_plan_changes(self):
        result = plan_changes(_base_state(insight_type="changes"))
        assert "get_kpi_summary" in result["planned_tools"]

    def test_plan_deep_dive(self):
        result = plan_deep_dive(_base_state(insight_type="deep_dive"))
        assert "get_kpi_summary" in result["planned_tools"]
        assert "get_active_anomaly_alerts" in result["planned_tools"]


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------


class TestFetchData:
    def test_calls_planned_tools(self):
        mock_kpi = {"today_gross": 1000}
        tools = {"get_kpi_summary": lambda: mock_kpi}
        state = _base_state(planned_tools=["get_kpi_summary"], _tools=tools)
        result = fetch_data(state)
        assert result["fetched_data"]["get_kpi_summary"] == mock_kpi

    def test_gracefully_handles_tool_failure(self):
        def bad_tool():
            raise RuntimeError("DB error")

        tools = {"get_kpi_summary": bad_tool}
        state = _base_state(planned_tools=["get_kpi_summary"], _tools=tools)
        result = fetch_data(state)
        assert result["fetched_data"] == {}
        assert len(result["errors"]) == 1

    def test_skips_missing_tools(self):
        tools = {}
        state = _base_state(planned_tools=["nonexistent_tool"], _tools=tools)
        result = fetch_data(state)
        assert result["fetched_data"] == {}
        assert result["errors"] == []


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_no_api_key_returns_no_output(self):
        state = _base_state(_openrouter_api_key="", fetched_data={})
        result = analyze(state)
        assert result["llm_raw_output"] is None
        assert result["llm_parsed_output"] is None

    def test_api_key_calls_openrouter(self):
        state = _base_state(
            _openrouter_api_key="sk-test",
            _openrouter_model="openai/gpt-4o-mini",
            fetched_data={"get_kpi_summary": {"today_gross": 1000}},
        )
        mock_response = '{"narrative": "Sales are good.", "highlights": ["Up 10%"]}'
        with patch(
            "datapulse.ai_light.graph.nodes._call_openrouter",
            return_value=(
                mock_response,
                {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            ),
        ):
            result = analyze(state)
        assert result["llm_raw_output"] == mock_response
        assert result["token_usage"]["total"] == 150


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_summary_output(self):
        state = _base_state(
            insight_type="summary",
            llm_parsed_output={"narrative": "Revenue is strong.", "highlights": ["Up 10%"]},
        )
        result = validate(state)
        trace = result["step_trace"]
        assert any(s["status"] == "ok" for s in trace)
        assert result["validation_retries"] == 0

    def test_invalid_output_increments_retries(self):
        state = _base_state(
            insight_type="summary",
            llm_parsed_output={"bad_field": "foo"},
        )
        result = validate(state)
        assert result["validation_retries"] == 1

    def test_none_output_increments_retries(self):
        state = _base_state(insight_type="summary", llm_parsed_output=None)
        result = validate(state)
        assert result["validation_retries"] == 1


# ---------------------------------------------------------------------------
# fallback
# ---------------------------------------------------------------------------


class TestFallback:
    def test_returns_degraded_narrative(self):
        state = _base_state(
            statistical_analysis={"mean": 1000.0, "stdev": 100.0, "min": 800.0, "max": 1200.0}
        )
        result = fallback(state)
        assert result["degraded"] is True
        assert "mean=1000.0" in result["narrative"]
        assert result["highlights"] == ["Statistical analysis used; AI narrative unavailable."]

    def test_no_stats_returns_generic_message(self):
        result = fallback(_base_state(statistical_analysis=None))
        assert result["degraded"] is True
        assert "error" in result["narrative"].lower()


# ---------------------------------------------------------------------------
# synthesize (Phase D: HITL)
# ---------------------------------------------------------------------------


class TestSynthesize:
    def test_composes_from_parsed_output(self):
        state = _base_state(
            llm_parsed_output={
                "narrative": "Sales grew 10%.",
                "highlights": ["Strong Q4"],
                "anomalies": [],
                "deltas": [],
            }
        )
        result = synthesize(state)
        assert result["narrative"] == "Sales grew 10%."
        assert result["highlights"] == ["Strong Q4"]
        assert result["degraded"] is False

    def test_human_edits_override_draft(self):
        """Phase D: human edits should take precedence over LLM draft."""
        state = _base_state(
            llm_parsed_output={"narrative": "Original draft.", "highlights": ["Original"]},
            human_edits={"narrative": "Analyst revised narrative."},
        )
        result = synthesize(state)
        assert result["narrative"] == "Analyst revised narrative."
        assert result["highlights"] == ["Original"]  # not overridden

    def test_empty_highlights_fallback(self):
        state = _base_state(llm_parsed_output={"narrative": "OK.", "highlights": None})
        result = synthesize(state)
        assert result["highlights"] == []


# ---------------------------------------------------------------------------
# cost_track
# ---------------------------------------------------------------------------


class TestCostTrack:
    def test_skips_when_no_session(self):
        state = _base_state()
        result = cost_track(state)
        assert "cost_track" in str(result)

    def test_writes_invocation_row(self):
        mock_session = MagicMock()
        state = _base_state(
            _session=mock_session,
            model_used="openai/gpt-4o-mini",
            token_usage={"input": 100, "output": 50, "total": 150},
            _start_ms=0,
        )
        with patch("datapulse.ai_light.graph.nodes.write_invocation_row") as mock_write:
            cost_track(state)
        mock_write.assert_called_once()
