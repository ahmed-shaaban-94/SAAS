"""Unit tests for AI-Light graph nodes — each node with a fake AILightState.

All tests are pure-unit: no real DB, no real LLM, no Redis.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from datapulse.ai_light.graph.state import AILightState

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_state(**overrides) -> AILightState:
    """Return a minimal valid AILightState with sensible defaults."""
    state: AILightState = {
        "tenant_id": "1",
        "run_id": "test-run-id",
        "insight_type": "summary",
        "target_date": "2026-04-12",
        "params_hash": "testhash",
        "cache_hit": False,
        "validation_retries": 0,
        "circuit_breaker_failures": 0,
        "degraded": False,
        "step_trace": [],
        "cost_cents": 0.0,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


# ---------------------------------------------------------------------------
# cache_check
# ---------------------------------------------------------------------------


class TestCacheCheckNode:
    def test_cache_miss(self):
        from datapulse.ai_light.graph.nodes import cache_check

        state = _base_state()
        with (
            patch("datapulse.ai_light.graph.nodes.cache_get", return_value=None),
            patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v1"),
        ):
            result = cache_check(state)

        assert result["cache_hit"] is False
        assert len(result["step_trace"]) == 1
        assert result["step_trace"][0]["node"] == "cache_check"

    def test_cache_hit(self):
        from datapulse.ai_light.graph.nodes import cache_check

        cached = {"narrative": "Cached text", "highlights": ["h1"], "degraded": False}
        state = _base_state()

        with (
            patch("datapulse.ai_light.graph.nodes.cache_get", return_value=cached),
            patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v1"),
        ):
            result = cache_check(state)

        assert result["cache_hit"] is True
        assert result["narrative"] == "Cached text"
        assert result["highlights"] == ["h1"]
        assert result["degraded"] is False

    def test_trace_entry_present(self):
        from datapulse.ai_light.graph.nodes import cache_check

        state = _base_state()
        with (
            patch("datapulse.ai_light.graph.nodes.cache_get", return_value=None),
            patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v0"),
        ):
            result = cache_check(state)

        entry = result["step_trace"][0]
        assert "ts" in entry
        assert entry["hit"] is False


# ---------------------------------------------------------------------------
# plan_summary
# ---------------------------------------------------------------------------


class TestPlanSummaryNode:
    def test_adds_trace(self):
        from datapulse.ai_light.graph.nodes import plan_summary

        state = _base_state()
        result = plan_summary(state)

        assert len(result["step_trace"]) == 1
        assert result["step_trace"][0]["node"] == "plan_summary"

    def test_plan_tools_listed(self):
        from datapulse.ai_light.graph.nodes import plan_summary

        state = _base_state()
        result = plan_summary(state)

        plan = result["step_trace"][0]["plan"]
        assert "get_kpi_summary" in plan
        assert "get_top_products" in plan
        assert "get_top_customers" in plan


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------


class TestFetchDataNode:
    def _make_tool(self, name: str, return_value: dict) -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.invoke.return_value = return_value
        return tool

    def test_summary_calls_three_tools(self):
        from datapulse.ai_light.graph.nodes import fetch_data

        kpi_tool = self._make_tool("get_kpi_summary", {"today_gross": "100"})
        prod_tool = self._make_tool("get_top_products", {"items": []})
        cust_tool = self._make_tool("get_top_customers", {"items": []})
        tools = [kpi_tool, prod_tool, cust_tool]

        state = _base_state()
        result = fetch_data(state, tools)

        kpi_tool.invoke.assert_called_once_with({"target_date": "2026-04-12"})
        prod_tool.invoke.assert_called_once_with({"limit": 5})
        cust_tool.invoke.assert_called_once_with({"limit": 5})

        assert result["kpi_data"] == {"today_gross": "100"}
        assert result["top_products"] == {"items": []}

    def test_tool_failure_recorded_in_errors(self):
        from datapulse.ai_light.graph.nodes import fetch_data

        kpi_tool = self._make_tool("get_kpi_summary", None)
        kpi_tool.invoke.side_effect = RuntimeError("DB down")
        prod_tool = self._make_tool("get_top_products", {"items": []})
        cust_tool = self._make_tool("get_top_customers", {"items": []})

        state = _base_state()
        result = fetch_data(state, [kpi_tool, prod_tool, cust_tool])

        assert any("get_kpi_summary" in e for e in result["errors"])
        assert "kpi_data" not in result


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


class TestAnalyzeNode:
    def _make_llm(self, content: str, tokens: dict | None = None) -> MagicMock:
        llm = MagicMock()
        response = MagicMock()
        response.content = content
        if tokens:
            response.usage_metadata = MagicMock(
                input_tokens=tokens.get("input", 0),
                output_tokens=tokens.get("output", 0),
                total_tokens=tokens.get("total", 0),
            )
        else:
            response.usage_metadata = None
        llm.invoke.return_value = response
        llm.model_name = "openai/gpt-4o-mini"
        return llm

    def test_valid_json_response(self):
        from datapulse.ai_light.graph.nodes import analyze

        payload = {"narrative": "Sales were strong.", "highlights": ["H1", "H2"]}
        llm = self._make_llm(json.dumps(payload))
        kpi = {
            "today_gross": 100000,
            "mtd_gross": 2000000,
            "ytd_gross": 10000000,
            "mom_growth_pct": 5.0,
            "yoy_growth_pct": 12.0,
            "daily_transactions": 120,
            "daily_customers": 95,
        }
        state = _base_state(
            kpi_data=kpi,
            top_products={
                "items": [
                    {"rank": 1, "name": "Drug A", "value": 50000, "pct_of_total": 40},
                ]
            },
            top_customers={
                "items": [
                    {"rank": 1, "name": "Hospital B", "value": 30000, "pct_of_total": 25},
                ]
            },
        )

        result = analyze(state, llm)

        assert result["llm_raw_output"] is not None
        assert result["llm_parsed_output"] == payload
        assert result["model_used"] == "openai/gpt-4o-mini"

    def test_invalid_json_sets_error(self):
        from datapulse.ai_light.graph.nodes import analyze

        llm = self._make_llm("This is not JSON at all.")
        state = _base_state(kpi_data={}, top_products={"items": []}, top_customers={"items": []})

        result = analyze(state, llm)

        assert result["llm_parsed_output"] is None
        assert result["errors"] is not None
        assert any("json_parse" in e for e in result["errors"])

    def test_llm_exception_sets_error(self):
        from datapulse.ai_light.graph.nodes import analyze

        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("API down")

        state = _base_state(kpi_data={}, top_products={"items": []}, top_customers={"items": []})
        result = analyze(state, llm)

        assert result["errors"] is not None
        assert any("llm:" in e for e in result["errors"])

    def test_statistical_analysis_populated(self):
        from datapulse.ai_light.graph.nodes import analyze

        payload = {"narrative": "Good.", "highlights": ["H1"]}
        llm = self._make_llm(json.dumps(payload))
        state = _base_state(
            kpi_data={},
            top_products={
                "items": [
                    {"rank": 1, "name": "A", "value": 100, "pct_of_total": 50},
                    {"rank": 2, "name": "B", "value": 200, "pct_of_total": 50},
                ]
            },
            top_customers={"items": []},
        )
        result = analyze(state, llm)
        assert "top_product_avg" in result["statistical_analysis"]


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidateNode:
    def test_valid_summary_output(self):
        from datapulse.ai_light.graph.nodes import validate

        state = _base_state(
            llm_parsed_output={
                "narrative": "Revenue was strong this week.",
                "highlights": ["H1", "H2"],
            },
            validation_retries=0,
        )
        result = validate(state)
        # retries should NOT increment on success
        assert result["validation_retries"] == 0

    def test_invalid_summary_output_increments_retries(self):
        from datapulse.ai_light.graph.nodes import validate

        state = _base_state(
            llm_parsed_output={"narrative": "", "highlights": []},  # fails validation
            validation_retries=0,
        )
        result = validate(state)
        assert result["validation_retries"] == 1

    def test_none_parsed_output_increments_retries(self):
        from datapulse.ai_light.graph.nodes import validate

        state = _base_state(llm_parsed_output=None, validation_retries=1)
        result = validate(state)
        assert result["validation_retries"] == 2


# ---------------------------------------------------------------------------
# synthesize
# ---------------------------------------------------------------------------


class TestSynthesizeNode:
    def test_extracts_narrative_and_highlights(self):
        from datapulse.ai_light.graph.nodes import synthesize

        state = _base_state(
            llm_parsed_output={
                "narrative": "Strong quarter.",
                "highlights": ["Up 10%", "New customers"],
            },
        )
        result = synthesize(state)

        assert result["narrative"] == "Strong quarter."
        assert result["highlights"] == ["Up 10%", "New customers"]
        assert result["degraded"] is False

    def test_empty_parsed_output(self):
        from datapulse.ai_light.graph.nodes import synthesize

        state = _base_state(llm_parsed_output={})
        result = synthesize(state)

        assert result["narrative"] == ""
        assert result["highlights"] == []


# ---------------------------------------------------------------------------
# fallback
# ---------------------------------------------------------------------------


class TestFallbackNode:
    def test_returns_degraded_true(self):
        from datapulse.ai_light.graph.nodes import fallback

        state = _base_state(
            kpi_data={"today_gross": 150000, "mtd_gross": 3000000, "ytd_gross": 12000000},
        )
        result = fallback(state)

        assert result["degraded"] is True
        assert isinstance(result["narrative"], str)
        assert len(result["narrative"]) > 0
        assert result["highlights"] == ["AI narrative unavailable — statistical summary shown."]

    def test_empty_kpi(self):
        from datapulse.ai_light.graph.nodes import fallback

        state = _base_state()
        result = fallback(state)
        assert result["degraded"] is True
        assert "Insufficient data" in result["narrative"]


# ---------------------------------------------------------------------------
# cache_write
# ---------------------------------------------------------------------------


class TestCacheWriteNode:
    def test_calls_cache_set(self):
        from datapulse.ai_light.graph.nodes import cache_write

        state = _base_state(
            narrative="Hello world.",
            highlights=["H1"],
            degraded=False,
        )
        with (
            patch("datapulse.ai_light.graph.nodes.cache_set") as mock_set,
            patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v1"),
        ):
            result = cache_write(state)
            mock_set.assert_called_once()

        assert len(result["step_trace"]) == 1

    def test_ttl_for_summary(self):
        from datapulse.ai_light.graph.nodes import cache_write

        state = _base_state(narrative="X", highlights=["Y"], degraded=False)
        captured = {}

        def fake_set(key, value, ttl=None):
            captured["ttl"] = ttl

        with (
            patch("datapulse.ai_light.graph.nodes.cache_set", side_effect=fake_set),
            patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v0"),
        ):
            cache_write(state)

        assert captured["ttl"] == 300  # _TTL_SUMMARY
