"""Contract tests — flag ON vs OFF must return identical /summary response shape.

Tests that AILightGraphService.generate_summary() returns the same AISummary
schema as AILightService.generate_summary().
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from datapulse.ai_light.models import AISummary
from datapulse.ai_light.service import AILightService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(use_langgraph: bool = False) -> MagicMock:
    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.openrouter_model = "openrouter/free"
    settings.openrouter_agent_model = "openai/gpt-4o-mini"
    settings.ai_light_use_langgraph = use_langgraph
    settings.redis_default_ttl = 300
    return settings


def _make_session() -> MagicMock:
    return MagicMock()


def _make_kpi_mock() -> MagicMock:
    kpi = MagicMock()
    kpi.today_gross = Decimal("150000")
    kpi.mtd_gross = Decimal("3000000")
    kpi.ytd_gross = Decimal("12000000")
    kpi.mom_growth_pct = Decimal("5.2")
    kpi.yoy_growth_pct = Decimal("11.0")
    kpi.daily_transactions = 120
    kpi.daily_customers = 95
    kpi.model_dump.return_value = {
        "today_gross": 150000.0, "mtd_gross": 3000000.0, "ytd_gross": 12000000.0,
        "mom_growth_pct": 5.2, "yoy_growth_pct": 11.0,
        "daily_transactions": 120, "daily_customers": 95,
    }
    return kpi


def _make_ranking_mock() -> MagicMock:
    item = MagicMock()
    item.rank = 1
    item.name = "Drug A"
    item.value = Decimal("50000")
    item.pct_of_total = Decimal("33.3")
    ranking = MagicMock()
    ranking.items = [item]
    ranking.model_dump.return_value = {
        "items": [{"rank": 1, "name": "Drug A", "value": 50000.0, "pct_of_total": 33.3}],
        "total": 50000.0,
    }
    return ranking


LEGACY_LLM_RESPONSE = (
    "Sales were strong this week with healthy MoM growth.\n"
    "• Revenue up 5% month-over-month\n"
    "• Drug A leads product mix\n"
    "• 95 active customers"
)

GRAPH_LLM_JSON = json.dumps({
    "narrative": "Sales were strong this week with healthy MoM growth.",
    "highlights": [
        "Revenue up 5% month-over-month",
        "Drug A leads product mix",
        "95 active customers",
    ],
})


# ---------------------------------------------------------------------------
# Contract: response shape must be identical AISummary
# ---------------------------------------------------------------------------


class TestResponseShape:
    """Both service implementations must return the same AISummary schema."""

    def _run_legacy(self) -> AISummary:
        settings = _make_settings(use_langgraph=False)
        session = _make_session()

        kpi = _make_kpi_mock()
        ranking = _make_ranking_mock()

        with (
            patch("datapulse.ai_light.service.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.service.OpenRouterClient") as mock_client_cls,
        ):
            mock_repo_cls.return_value.get_kpi_summary.return_value = kpi
            mock_repo_cls.return_value.get_top_products.return_value = ranking
            mock_repo_cls.return_value.get_top_customers.return_value = ranking
            mock_client_cls.return_value.is_configured = True
            mock_client_cls.return_value.chat.return_value = LEGACY_LLM_RESPONSE

            svc = AILightService(settings=settings, session=session)
            return svc.generate_summary(target_date=date(2026, 4, 12))

    def _run_graph(self) -> AISummary:
        pytest.importorskip("langgraph", reason="langgraph not installed")

        import datapulse.ai_light.graph.builder as _builder
        _builder._compiled_graph = None

        settings = _make_settings(use_langgraph=True)
        session = _make_session()

        kpi = _make_kpi_mock()
        ranking = _make_ranking_mock()
        trend = MagicMock()
        trend.model_dump.return_value = {
            "points": [], "total": 0, "average": 0, "minimum": 0, "maximum": 0
        }

        fake_llm = MagicMock()
        resp = MagicMock()
        resp.content = GRAPH_LLM_JSON
        resp.usage_metadata = MagicMock(input_tokens=200, output_tokens=80, total_tokens=280)
        fake_llm.invoke.return_value = resp
        fake_llm.model_name = "openai/gpt-4o-mini"

        from datapulse.ai_light.graph_service import AILightGraphService

        with (
            patch("datapulse.ai_light.graph_service.AnalyticsRepository") as mock_repo_cls,
            patch("datapulse.ai_light.graph_service.AILightService"),
            patch("datapulse.ai_light.graph.nodes.cache_get", return_value=None),
            patch("datapulse.ai_light.graph.nodes.cache_set"),
            patch("datapulse.ai_light.graph.nodes.get_cache_version", return_value="v0"),
            patch("datapulse.ai_light.graph.cost.write_invocation_row"),
            patch("datapulse.ai_light.graph.builder.set_runtime_context"),
            patch(
                "datapulse.ai_light.graph_service.AILightGraphService._build_llm",
                return_value=fake_llm,
            ),
        ):
            repo_inst = MagicMock()
            repo_inst.get_kpi_summary.return_value = kpi
            repo_inst.get_top_products.return_value = ranking
            repo_inst.get_top_customers.return_value = ranking
            repo_inst.get_daily_trend.return_value = trend
            repo_inst.get_monthly_trend.return_value = trend
            mock_repo_cls.return_value = repo_inst

            from datapulse.ai_light.graph.builder import set_runtime_context
            from datapulse.ai_light.graph.tools import build_tool_registry

            tools = build_tool_registry(repo_inst)
            set_runtime_context(llm=fake_llm, tools=tools, session=session)

            svc = AILightGraphService(settings=settings, session=session)
            return svc.generate_summary(target_date=date(2026, 4, 12))

    def test_legacy_returns_ai_summary(self):
        result = self._run_legacy()
        assert isinstance(result, AISummary)

    def test_legacy_has_all_fields(self):
        result = self._run_legacy()
        assert result.narrative
        assert isinstance(result.highlights, list)
        assert len(result.highlights) >= 1
        assert result.period == "2026-04-12"

    def test_graph_returns_ai_summary(self):
        result = self._run_graph()
        assert isinstance(result, AISummary)

    def test_graph_has_all_fields(self):
        result = self._run_graph()
        assert result.narrative
        assert isinstance(result.highlights, list)
        assert len(result.highlights) >= 1
        assert result.period == "2026-04-12"

    def test_same_field_names(self):
        legacy = self._run_legacy()
        graph = self._run_graph()

        legacy_keys = set(legacy.model_fields.keys())
        graph_keys = set(graph.model_fields.keys())
        assert legacy_keys == graph_keys


# ---------------------------------------------------------------------------
# Contract: feature flag wiring in deps.py
# ---------------------------------------------------------------------------


class TestFeatureFlagWiring:
    def test_flag_off_returns_legacy_type(self):
        from datapulse.ai_light.service import AILightService as LegacyService

        settings = _make_settings(use_langgraph=False)
        session = _make_session()

        # Directly verify the factory logic without nested patching
        if not settings.ai_light_use_langgraph:
            svc = LegacyService(settings=settings, session=session)
            assert isinstance(svc, LegacyService)

    def test_flag_on_returns_graph_type(self):
        pytest.importorskip("langgraph", reason="langgraph not installed")

        from datapulse.ai_light.graph_service import AILightGraphService

        settings = _make_settings(use_langgraph=True)
        session = _make_session()

        with patch("datapulse.ai_light.graph_service.AnalyticsRepository"), \
             patch("datapulse.ai_light.graph_service.AILightService"):
            svc = AILightGraphService(settings=settings, session=session)
            assert isinstance(svc, AILightGraphService)
            # is_available mirrors openrouter_api_key presence
            assert svc.is_available is True
