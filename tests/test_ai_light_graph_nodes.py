"""Unit tests for AI Light graph nodes.

Nodes are tested as pure functions — no LangGraph, no DB, no network.
Each test passes a minimal state dict and asserts on the returned delta.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from datapulse.ai_light.graph.nodes import (
    fallback,
    plan_anomalies,
    plan_changes,
    plan_summary,
    synthesize,
    validate,
)

# ── helpers ───────────────────────────────────────────────────────────────


def _state(**kwargs):
    defaults = {
        "insight_type": "summary",
        "tenant_id": "1",
        "run_id": "test-run",
        "validation_retries": 0,
        "errors": [],
        "degraded": False,
        "step_trace": [],
    }
    defaults.update(kwargs)
    return defaults


# ── plan_summary ──────────────────────────────────────────────────────────


class TestPlanSummary:
    def test_returns_step_trace(self):
        result = plan_summary(_state())
        assert "step_trace" in result
        assert result["step_trace"][0]["node"] == "plan_summary"

    def test_declares_tools(self):
        result = plan_summary(_state())
        plan = result["_tools_plan"]
        assert "get_kpi_summary" in plan
        assert "get_top_products" in plan
        assert "get_top_customers" in plan


# ── plan_anomalies ────────────────────────────────────────────────────────


class TestPlanAnomalies:
    def test_returns_step_trace(self):
        result = plan_anomalies(_state(insight_type="anomalies"))
        assert result["step_trace"][0]["node"] == "plan_anomalies"

    def test_declares_anomaly_tools(self):
        result = plan_anomalies(_state(insight_type="anomalies"))
        plan = result["_tools_plan"]
        assert "get_daily_trend" in plan
        assert "get_active_anomaly_alerts" in plan

    def test_does_not_include_summary_tools(self):
        result = plan_anomalies(_state(insight_type="anomalies"))
        plan = result["_tools_plan"]
        assert "get_kpi_summary" not in plan


# ── plan_changes ──────────────────────────────────────────────────────────


class TestPlanChanges:
    def test_returns_step_trace(self):
        result = plan_changes(_state(insight_type="changes"))
        assert result["step_trace"][0]["node"] == "plan_changes"

    def test_declares_changes_tools(self):
        result = plan_changes(_state(insight_type="changes"))
        plan = result["_tools_plan"]
        assert "get_kpi_current" in plan
        assert "get_kpi_previous" in plan
        assert "get_top_gainers" in plan
        assert "get_top_losers" in plan
        assert "get_top_staff" in plan


# ── validate node ─────────────────────────────────────────────────────────


class TestValidate:
    def test_ok_when_parsed_present_and_valid_summary(self):
        state = _state(
            insight_type="summary",
            llm_parsed_output={"narrative": "Good day", "highlights": ["H1"]},
        )
        result = validate(state)
        assert result["step_trace"][0]["result"] == "ok"
        assert "validation_retries" not in result

    def test_ok_when_parsed_present_and_valid_anomalies(self):
        state = _state(
            insight_type="anomalies",
            llm_parsed_output={
                "anomalies": [{"date": "2026-01-01", "description": "drop", "severity": "high"}],
                "narrative": "One spike",
            },
        )
        result = validate(state)
        assert result["step_trace"][0]["result"] == "ok"

    def test_ok_when_parsed_present_and_valid_changes(self):
        state = _state(
            insight_type="changes",
            llm_parsed_output={"narrative": "Sales grew", "key_changes": ["K1"]},
        )
        result = validate(state)
        assert result["step_trace"][0]["result"] == "ok"

    def test_increments_retries_when_no_parsed_output(self):
        state = _state(insight_type="summary", llm_parsed_output=None)
        result = validate(state)
        assert result["validation_retries"] == 1
        assert result["step_trace"][0]["result"] == "no_output"

    def test_increments_retries_on_schema_failure(self):
        # Missing required "narrative" field
        state = _state(
            insight_type="summary",
            llm_parsed_output={"highlights": ["H1"]},
        )
        result = validate(state)
        assert result["validation_retries"] == 1
        assert result["step_trace"][0]["result"] == "failed"

    def test_stacks_retries(self):
        state = _state(
            insight_type="summary",
            llm_parsed_output=None,
            validation_retries=1,
        )
        result = validate(state)
        assert result["validation_retries"] == 2

    def test_unknown_insight_type_passes_through(self):
        state = _state(insight_type="deep_dive", llm_parsed_output={"foo": "bar"})
        result = validate(state)
        assert result["step_trace"][0]["result"] == "unknown_type"

    def test_malformed_llm_response_fires_retry(self):
        """Injecting a malformed LLM response triggers validation failure."""
        state = _state(
            insight_type="anomalies",
            # anomalies list items missing required fields
            llm_parsed_output={"anomalies": [{"bad_key": "x"}], "narrative": "ok"},
        )
        # AnomalyItem requires date, description, severity
        result = validate(state)
        assert result["validation_retries"] == 1
        assert any("validation:" in e for e in (result.get("errors") or []))


# ── fallback node ─────────────────────────────────────────────────────────


class TestFallback:
    def test_degraded_true(self):
        result = fallback(_state(insight_type="summary", kpi_data={}))
        assert result["degraded"] is True

    def test_summary_returns_correct_shape(self):
        state = _state(
            insight_type="summary",
            kpi_data={"today_gross": 100000.0, "mtd_gross": 3000000.0},
        )
        result = fallback(state)
        assert isinstance(result["narrative"], str)
        assert isinstance(result["highlights"], list)
        assert result["anomalies_list"] is None
        assert result["deltas"] is None

    def test_anomalies_returns_correct_shape(self):
        state = _state(
            insight_type="anomalies",
            statistical_analysis={"avg": 5000.0, "std": 1000.0},
        )
        result = fallback(state)
        assert isinstance(result["narrative"], str)
        assert result["anomalies_list"] == []
        assert result["highlights"] is None
        assert result["deltas"] is None

    def test_changes_returns_correct_shape(self):
        state = _state(
            insight_type="changes",
            statistical_analysis={
                "deltas": [
                    {
                        "metric": "today_gross",
                        "current_value": 120000.0,
                        "previous_value": 100000.0,
                        "change_pct": 20.0,
                        "direction": "up",
                    }
                ]
            },
        )
        result = fallback(state)
        assert isinstance(result["narrative"], str)
        assert isinstance(result["deltas"], list)
        assert result["anomalies_list"] is None

    def test_fallback_degraded_flag_preserved_through_synthesize_shape(self):
        """Verify fallback and synthesize produce the same key set."""
        fb = fallback(_state(insight_type="summary", kpi_data={}))
        sy = synthesize(
            _state(
                insight_type="summary",
                llm_parsed_output={"narrative": "x", "highlights": ["h"]},
                statistical_analysis={},
            )
        )
        # Both must return the same set of output keys
        expected_keys = {
            "narrative",
            "highlights",
            "anomalies_list",
            "deltas",
            "degraded",
            "step_trace",
        }
        assert expected_keys.issubset(fb.keys())
        assert expected_keys.issubset(sy.keys())


# ── synthesize node ───────────────────────────────────────────────────────


class TestSynthesize:
    def test_summary_extracts_narrative_and_highlights(self):
        state = _state(
            insight_type="summary",
            llm_parsed_output={"narrative": "Great month", "highlights": ["H1", "H2"]},
            statistical_analysis={},
        )
        result = synthesize(state)
        assert result["narrative"] == "Great month"
        assert result["highlights"] == ["H1", "H2"]
        assert result["degraded"] is False

    def test_anomalies_extracts_list(self):
        state = _state(
            insight_type="anomalies",
            llm_parsed_output={
                "anomalies": [
                    {"date": "2026-01-05", "description": "Big drop", "severity": "high"}
                ],
                "narrative": "One spike detected",
            },
            statistical_analysis={"avg": 5000, "std": 1000},
        )
        result = synthesize(state)
        assert len(result["anomalies_list"]) == 1
        assert result["anomalies_list"][0]["severity"] == "high"
        assert result["degraded"] is False

    def test_anomalies_sanitizes_invalid_severity(self):
        state = _state(
            insight_type="anomalies",
            llm_parsed_output={
                "anomalies": [{"date": "2026-01-05", "description": "x", "severity": "CRITICAL"}],
                "narrative": "",
            },
            statistical_analysis={},
        )
        result = synthesize(state)
        assert result["anomalies_list"][0]["severity"] == "low"

    def test_changes_extracts_narrative_and_deltas(self):
        deltas = [
            {
                "metric": "today_gross",
                "current_value": 120000.0,
                "previous_value": 100000.0,
                "change_pct": 20.0,
                "direction": "up",
            }
        ]
        state = _state(
            insight_type="changes",
            llm_parsed_output={"narrative": "Sales up 20%", "key_changes": ["K1"]},
            statistical_analysis={"deltas": deltas},
        )
        result = synthesize(state)
        assert result["narrative"] == "Sales up 20%"
        assert result["highlights"] == ["K1"]
        assert result["deltas"] == deltas


# ── make_fetch_data_node ──────────────────────────────────────────────────


class TestFetchDataNode:
    def _make_tools(self, **overrides):
        kpi_data = {"today_gross": 100000.0, "mtd_gross": 3000000.0}
        trend_data = {"points": [{"period": "2026-01-01", "value": 50000.0}]}
        ranking_data = {"items": [], "total": 0, "active_count": 0}
        alerts_data = {"alerts": []}
        tools = {
            "get_kpi_summary": MagicMock(return_value=kpi_data),
            "get_daily_trend": MagicMock(return_value=trend_data),
            "get_monthly_trend": MagicMock(return_value=trend_data),
            "get_top_products": MagicMock(return_value=ranking_data),
            "get_top_customers": MagicMock(return_value=ranking_data),
            "get_top_staff": MagicMock(return_value=ranking_data),
            "get_site_performance": MagicMock(return_value=ranking_data),
            "get_top_gainers": MagicMock(return_value={"gainers": [], "entity_type": "product"}),
            "get_top_losers": MagicMock(return_value={"losers": [], "entity_type": "product"}),
            "get_active_anomaly_alerts": MagicMock(return_value=alerts_data),
        }
        tools.update(overrides)
        return tools

    def test_summary_calls_correct_tools(self):
        from datapulse.ai_light.graph.nodes import make_fetch_data_node

        tools = self._make_tools()
        node = make_fetch_data_node(tools)
        result = node(_state(insight_type="summary"))
        tools["get_kpi_summary"].assert_called_once()
        tools["get_top_products"].assert_called_once()
        tools["get_top_customers"].assert_called_once()
        assert "kpi_data" in result

    def test_anomalies_calls_correct_tools(self):
        from datapulse.ai_light.graph.nodes import make_fetch_data_node

        tools = self._make_tools()
        node = make_fetch_data_node(tools)
        result = node(
            _state(
                insight_type="anomalies",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 4, 1),
            )
        )
        tools["get_daily_trend"].assert_called_once()
        tools["get_active_anomaly_alerts"].assert_called_once()
        assert "daily_trend" in result
        assert "anomaly_alerts" in result

    def test_changes_calls_correct_tools(self):
        from datapulse.ai_light.graph.nodes import make_fetch_data_node

        tools = self._make_tools()
        node = make_fetch_data_node(tools)
        result = node(
            _state(
                insight_type="changes",
                current_date=date(2026, 4, 1),
                previous_date=date(2026, 3, 1),
            )
        )
        assert tools["get_kpi_summary"].call_count == 2  # current + previous
        tools["get_top_gainers"].assert_called_once()
        tools["get_top_losers"].assert_called_once()
        assert "kpi_current" in result
        assert "kpi_previous" in result

    def test_fetch_data_error_appended_to_errors(self):
        from datapulse.ai_light.graph.nodes import make_fetch_data_node

        tools = self._make_tools(get_kpi_summary=MagicMock(side_effect=RuntimeError("DB down")))
        node = make_fetch_data_node(tools)
        result = node(_state(insight_type="summary"))
        assert any("fetch_data" in e for e in result.get("errors", []))


# ── make_analyze_node ─────────────────────────────────────────────────────


class TestAnalyzeNode:
    def _mock_client(self, response: str = '{"narrative":"ok","highlights":["H1"]}'):
        client = MagicMock()
        client.is_configured = True
        client.chat = MagicMock(return_value=response)
        return client

    def _mock_settings(self):
        s = MagicMock()
        s.openrouter_model = "openrouter/free"
        return s

    def test_summary_sets_statistical_analysis(self):
        from datapulse.ai_light.graph.nodes import make_analyze_node

        client = self._mock_client()
        node = make_analyze_node(client, self._mock_settings())
        result = node(
            _state(
                insight_type="summary",
                kpi_data={
                    "today_gross": 100000.0,
                    "mtd_gross": 3000000.0,
                    "ytd_gross": 30000000.0,
                    "mom_growth_pct": 5.0,
                    "yoy_growth_pct": 10.0,
                    "daily_transactions": 50,
                    "daily_customers": 30,
                },
                top_products={"items": []},
                top_customers={"items": []},
            )
        )
        assert result.get("statistical_analysis") is not None
        assert result.get("llm_parsed_output") is not None

    def test_anomalies_builds_stat_analysis(self):
        from datapulse.ai_light.graph.nodes import make_analyze_node

        client = self._mock_client('{"anomalies":[],"narrative":"all normal"}')
        node = make_analyze_node(client, self._mock_settings())
        points = [{"period": f"2026-01-{i:02d}", "value": 5000 + i * 100} for i in range(1, 10)]
        result = node(
            _state(
                insight_type="anomalies",
                daily_trend={"points": points},
                anomaly_alerts=[],
            )
        )
        stat = result.get("statistical_analysis", {})
        assert "avg" in stat
        assert "std" in stat

    def test_changes_builds_stat_analysis(self):
        from datapulse.ai_light.graph.nodes import make_analyze_node

        client = self._mock_client('{"narrative":"up","key_changes":["sales up"]}')
        node = make_analyze_node(client, self._mock_settings())
        kpi = {
            "today_gross": 100000.0,
            "mtd_gross": 3000000.0,
            "ytd_gross": 30000000.0,
            "daily_transactions": 50,
            "daily_customers": 30,
        }
        result = node(
            _state(
                insight_type="changes",
                kpi_current={**kpi},
                kpi_previous={k: v * 0.9 for k, v in kpi.items()},
                current_date=date(2026, 4, 1),
                previous_date=date(2026, 3, 1),
                top_gainers={"gainers": []},
                top_losers={"losers": []},
                top_staff={"items": []},
            )
        )
        assert "deltas" in result.get("statistical_analysis", {})

    def test_skips_llm_when_not_configured(self):
        from datapulse.ai_light.graph.nodes import make_analyze_node

        client = MagicMock()
        client.is_configured = False
        node = make_analyze_node(client, self._mock_settings())
        result = node(
            _state(insight_type="summary", kpi_data={}, top_products={}, top_customers={})
        )
        assert result.get("llm_parsed_output") is None
        client.chat.assert_not_called()

    def test_json_parse_error_recorded_in_errors(self):
        from datapulse.ai_light.graph.nodes import make_analyze_node

        client = self._mock_client("this is not json at all")
        node = make_analyze_node(client, self._mock_settings())
        result = node(
            _state(
                insight_type="summary",
                kpi_data={
                    "today_gross": 1.0,
                    "mtd_gross": 1.0,
                    "ytd_gross": 1.0,
                    "mom_growth_pct": 0,
                    "yoy_growth_pct": 0,
                    "daily_transactions": 0,
                    "daily_customers": 0,
                },
                top_products={"items": []},
                top_customers={"items": []},
            )
        )
        assert any("json_parse" in e for e in (result.get("errors") or []))
