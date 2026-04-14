"""Integration tests for the AI Light graph (mocked LLM, mocked DB).

The full graph is invoked end-to-end. LangGraph must be importable;
if it isn't, the test module is skipped. The OpenRouter client and all
DB repositories are mocked so no network or DB access is needed.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if langgraph is not installed
langgraph = pytest.importorskip(
    "langgraph", reason="langgraph not installed — skipping graph integration tests"
)


def _make_session():
    """Return a minimal mock Session that satisfies repository constructors."""
    session = MagicMock()
    # execute().fetchall() / fetchone() / scalar()
    session.execute.return_value.fetchall.return_value = []
    session.execute.return_value.fetchone.return_value = None
    session.execute.return_value.scalar.return_value = None
    return session


def _make_settings(use_langgraph: bool = True):
    s = MagicMock()
    s.openrouter_api_key = "sk-test"
    s.openrouter_model = "openrouter/free"
    s.ai_light_use_langgraph = use_langgraph
    return s


# ── summary path ──────────────────────────────────────────────────────────


class TestGraphSummaryPath:
    def _run(self, llm_response: str = '{"narrative":"Sales strong","highlights":["H1"]}'):
        from datapulse.ai_light.graph.builder import build_graph

        session = _make_session()
        settings = _make_settings()

        kpi = {
            "today_gross": 100000.0,
            "mtd_gross": 3000000.0,
            "ytd_gross": 30000000.0,
            "mom_growth_pct": 5.0,
            "yoy_growth_pct": 10.0,
            "daily_transactions": 50,
            "daily_customers": 30,
        }
        ranking = {"items": [], "total": 0.0, "active_count": 0}

        with (
            patch("datapulse.ai_light.graph.tools.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.client.httpx.post") as mock_post,
            patch("datapulse.ai_light.graph.cost.write_invocation_row"),
        ):
            mock_repo_inst = mock_repo_cls.return_value
            kpi_mock = MagicMock(**kpi, model_dump=MagicMock(return_value=kpi))
            ranking_mock = MagicMock(model_dump=MagicMock(return_value=ranking))
            mock_repo_inst.get_kpi_summary.return_value = kpi_mock
            mock_repo_inst.get_top_products.return_value = ranking_mock
            mock_repo_inst.get_top_customers.return_value = ranking_mock

            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": llm_response}}],
                "usage": {"total_tokens": 100},
            }
            mock_post.return_value = mock_resp

            graph = build_graph(session, settings)
            return graph.invoke(
                {
                    "insight_type": "summary",
                    "run_id": "test-run-summary",
                    "tenant_id": "1",
                    "target_date": date(2026, 4, 12),
                    "validation_retries": 0,
                    "circuit_breaker_failures": 0,
                    "cache_hit": False,
                    "degraded": False,
                    "step_trace": [],
                    "errors": [],
                }
            )

    def test_summary_happy_path_returns_narrative(self):
        result = self._run()
        assert result.get("narrative") == "Sales strong"
        assert result.get("highlights") == ["H1"]
        assert result.get("degraded") is False

    def test_summary_step_trace_records_nodes(self):
        result = self._run()
        nodes_visited = [t["node"] for t in (result.get("step_trace") or [])]
        assert "plan_summary" in nodes_visited
        assert "fetch_data" in nodes_visited
        assert "analyze" in nodes_visited
        assert "validate" in nodes_visited


# ── anomalies path ────────────────────────────────────────────────────────


class TestGraphAnomaliesPath:
    def _run(
        self,
        llm_response: str = (
            '{"anomalies":[{"date":"2026-01-05","description":"drop",'
            '"severity":"high"}],"narrative":"one spike"}'
        ),
    ):
        from datapulse.ai_light.graph.builder import build_graph

        session = _make_session()
        settings = _make_settings()

        points = [{"period": f"2026-01-{i:02d}", "value": 5000.0 + i * 100} for i in range(1, 31)]
        trend_data = {"points": points}

        with (
            patch("datapulse.ai_light.graph.tools.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.graph.tools.AnomalyRepository") as mock_alert_cls,
            patch("datapulse.ai_light.client.httpx.post") as mock_post,
            patch("datapulse.ai_light.graph.cost.write_invocation_row"),
        ):
            mock_repo_inst = mock_repo_cls.return_value
            mock_repo_inst.get_daily_trend.return_value = MagicMock(
                model_dump=MagicMock(return_value=trend_data)
            )
            mock_alert_cls.return_value.get_active_alerts.return_value = []

            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": llm_response}}],
                "usage": {"total_tokens": 80},
            }
            mock_post.return_value = mock_resp

            graph = build_graph(session, settings)
            return graph.invoke(
                {
                    "insight_type": "anomalies",
                    "run_id": "test-run-anomalies",
                    "tenant_id": "1",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 1, 31),
                    "validation_retries": 0,
                    "circuit_breaker_failures": 0,
                    "cache_hit": False,
                    "degraded": False,
                    "step_trace": [],
                    "errors": [],
                }
            )

    def test_anomalies_happy_path(self):
        result = self._run()
        anomalies = result.get("anomalies_list") or []
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "high"
        assert result.get("degraded") is False

    def test_anomalies_narrative_set(self):
        result = self._run()
        assert result.get("narrative") == "one spike"

    def test_anomalies_step_trace_includes_plan_anomalies(self):
        result = self._run()
        nodes = [t["node"] for t in (result.get("step_trace") or [])]
        assert "plan_anomalies" in nodes


# ── changes path ──────────────────────────────────────────────────────────


class TestGraphChangesPath:
    def _run(
        self,
        llm_response: str = '{"narrative":"Sales up 20%","key_changes":["Gross up","Txns stable"]}',
    ):
        from datapulse.ai_light.graph.builder import build_graph

        session = _make_session()
        settings = _make_settings()

        kpi = {
            "today_gross": 120000.0,
            "mtd_gross": 3600000.0,
            "ytd_gross": 36000000.0,
            "mom_growth_pct": 20.0,
            "yoy_growth_pct": 15.0,
            "daily_transactions": 60,
            "daily_customers": 35,
        }
        ranking = {"items": [], "total": 0.0, "active_count": 0}
        with (
            patch("datapulse.ai_light.graph.tools.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.graph.tools.ComparisonRepository") as mock_comp_cls,
            patch("datapulse.ai_light.client.httpx.post") as mock_post,
            patch("datapulse.ai_light.graph.cost.write_invocation_row"),
        ):
            mock_repo_inst = mock_repo_cls.return_value
            mock_repo_inst.get_kpi_summary.return_value = MagicMock(
                model_dump=MagicMock(return_value=kpi)
            )
            mock_repo_inst.get_top_staff.return_value = MagicMock(
                model_dump=MagicMock(return_value=ranking)
            )
            mock_comp_cls.return_value.get_top_movers.return_value = MagicMock(
                gainers=[], losers=[]
            )

            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": llm_response}}],
                "usage": {"total_tokens": 90},
            }
            mock_post.return_value = mock_resp

            graph = build_graph(session, settings)
            return graph.invoke(
                {
                    "insight_type": "changes",
                    "run_id": "test-run-changes",
                    "tenant_id": "1",
                    "current_date": date(2026, 4, 12),
                    "previous_date": date(2026, 3, 12),
                    "validation_retries": 0,
                    "circuit_breaker_failures": 0,
                    "cache_hit": False,
                    "degraded": False,
                    "step_trace": [],
                    "errors": [],
                }
            )

    def test_changes_happy_path(self):
        result = self._run()
        assert result.get("narrative") == "Sales up 20%"
        assert result.get("highlights") == ["Gross up", "Txns stable"]
        assert result.get("degraded") is False

    def test_changes_deltas_populated(self):
        result = self._run()
        deltas = result.get("deltas")
        assert deltas is not None
        assert isinstance(deltas, list)

    def test_changes_step_trace_includes_plan_changes(self):
        result = self._run()
        nodes = [t["node"] for t in (result.get("step_trace") or [])]
        assert "plan_changes" in nodes
        assert "fetch_data" in nodes


# ── validation retry + fallback ───────────────────────────────────────────


class TestValidationRetryAndFallback:
    """Inject malformed LLM responses — verify retry fires twice then fallback activates."""

    def _run_anomalies_with_bad_llm(self):
        from datapulse.ai_light.graph.builder import build_graph

        session = _make_session()
        settings = _make_settings()
        points = [{"period": f"2026-01-{i:02d}", "value": 5000.0} for i in range(1, 10)]

        with (
            patch("datapulse.ai_light.graph.tools.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.graph.tools.AnomalyRepository") as mock_alert_cls,
            patch("datapulse.ai_light.client.httpx.post") as mock_post,
            patch("datapulse.ai_light.graph.cost.write_invocation_row"),
        ):
            mock_repo_inst = mock_repo_cls.return_value
            mock_repo_inst.get_daily_trend.return_value = MagicMock(
                model_dump=MagicMock(return_value={"points": points})
            )
            mock_alert_cls.return_value.get_active_alerts.return_value = []

            # Always return malformed JSON — missing required fields in anomaly items
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            bad_content = '{"anomalies":[{"bad":"x"}],"narrative":"ok"}'
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": bad_content}}],
                "usage": {"total_tokens": 50},
            }
            mock_post.return_value = mock_resp

            graph = build_graph(session, settings)
            return graph.invoke(
                {
                    "insight_type": "anomalies",
                    "run_id": "test-retry",
                    "tenant_id": "1",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 1, 9),
                    "validation_retries": 0,
                    "circuit_breaker_failures": 0,
                    "cache_hit": False,
                    "degraded": False,
                    "step_trace": [],
                    "errors": [],
                }
            )

    def test_malformed_response_activates_fallback(self):
        result = self._run_anomalies_with_bad_llm()
        assert result.get("degraded") is True

    def test_fallback_preserves_anomaly_report_shape(self):
        result = self._run_anomalies_with_bad_llm()
        # anomalies_list must exist (empty list) even in fallback
        assert result.get("anomalies_list") is not None
        assert isinstance(result.get("anomalies_list"), list)
        assert isinstance(result.get("narrative"), str)

    def test_validation_retries_reaches_max(self):
        result = self._run_anomalies_with_bad_llm()
        assert (result.get("validation_retries") or 0) >= 2

    def test_llm_called_multiple_times_on_retry(self):
        from datapulse.ai_light.graph.builder import build_graph

        session = _make_session()
        settings = _make_settings()
        points = [{"period": f"2026-01-{i:02d}", "value": 5000.0} for i in range(1, 5)]
        call_count = {"n": 0}

        with (
            patch("datapulse.ai_light.graph.tools.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.graph.tools.AnomalyRepository") as mock_alert_cls,
            patch("datapulse.ai_light.client.httpx.post") as mock_post,
            patch("datapulse.ai_light.graph.cost.write_invocation_row"),
        ):
            mock_repo_inst = mock_repo_cls.return_value
            mock_repo_inst.get_daily_trend.return_value = MagicMock(
                model_dump=MagicMock(return_value={"points": points})
            )
            mock_alert_cls.return_value.get_active_alerts.return_value = []

            def _bad_response(*args, **kwargs):
                call_count["n"] += 1
                r = MagicMock()
                r.raise_for_status = MagicMock()
                bad_c = '{"anomalies":[{"x":"y"}],"narrative":""}'
                r.json.return_value = {
                    "choices": [{"message": {"content": bad_c}}],
                    "usage": {"total_tokens": 10},
                }
                return r

            mock_post.side_effect = _bad_response

            graph = build_graph(session, settings)
            graph.invoke(
                {
                    "insight_type": "anomalies",
                    "run_id": "test-retry-count",
                    "tenant_id": "1",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 1, 4),
                    "validation_retries": 0,
                    "circuit_breaker_failures": 0,
                    "cache_hit": False,
                    "degraded": False,
                    "step_trace": [],
                    "errors": [],
                }
            )

        # Initial analyze + up to 2 retries = up to 3 LLM calls
        assert call_count["n"] >= 2
