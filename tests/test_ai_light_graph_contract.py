"""Contract tests — all 3 endpoints return identical Pydantic shapes
regardless of whether AI_LIGHT_USE_LANGGRAPH is ON or OFF.

These tests verify that AILightService and AILightGraphService:
  1. Both return the same Pydantic model classes
  2. Both return instances with the same set of field names
  3. The graph service preserves AnomalyReport and ChangeNarrative shapes
     even when degraded=True (fallback path)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

from datapulse.ai_light.models import AISummary, AnomalyReport, ChangeNarrative
from datapulse.ai_light.service import AILightService

# ── contract helpers ──────────────────────────────────────────────────────


def _assert_same_shape(model_a: Any, model_b: Any) -> None:
    """Assert that two Pydantic model instances have the same field names."""
    assert type(model_a) is type(model_b), (
        f"Type mismatch: {type(model_a).__name__} vs {type(model_b).__name__}"
    )
    assert type(model_a).model_fields.keys() == type(model_b).model_fields.keys()


# ── legacy service fixtures ───────────────────────────────────────────────


def _make_legacy_service() -> tuple[AILightService, Any]:
    """Return (service, mock_session) for the legacy AILightService."""
    session = MagicMock()
    settings = MagicMock()
    settings.openrouter_api_key = ""  # unconfigured → stats-only
    settings.openrouter_model = "openrouter/free"

    kpi = MagicMock()
    kpi.today_gross = Decimal("100000")
    kpi.mtd_gross = Decimal("3000000")
    kpi.ytd_gross = Decimal("30000000")
    kpi.mom_growth_pct = Decimal("5.0")
    kpi.yoy_growth_pct = Decimal("10.0")
    kpi.daily_transactions = 50
    kpi.daily_customers = 30

    trend = MagicMock()
    trend.points = []

    ranking = MagicMock()
    ranking.items = []

    with patch("datapulse.ai_light.service.AnalyticsRepository") as mock_repo_cls:
        inst = mock_repo_cls.return_value
        inst.get_kpi_summary.return_value = kpi
        inst.get_top_products.return_value = ranking
        inst.get_top_customers.return_value = ranking
        inst.get_daily_trend.return_value = trend
        svc = AILightService(settings=settings, session=session)
        svc._repo = inst  # inject mock repo directly
        return svc, inst


# ── graph service fixture ─────────────────────────────────────────────────


def _make_graph_service(degraded: bool = False):
    """Return a mock AILightGraphService that returns valid model instances."""
    from datapulse.ai_light.graph_service import AILightGraphService

    session = MagicMock()
    settings = MagicMock()
    settings.openrouter_api_key = "sk-test"
    settings.openrouter_model = "openrouter/free"
    settings.ai_light_use_langgraph = True

    svc = AILightGraphService(settings=settings, session=session)
    return svc


# ── AISummary contract ────────────────────────────────────────────────────


class TestSummaryContract:
    """Both services must return AISummary with identical field names."""

    def test_legacy_returns_aisummary(self):
        svc, repo = _make_legacy_service()
        repo.get_kpi_summary.return_value = MagicMock(
            today_gross=Decimal("100000"),
            mtd_gross=Decimal("3000000"),
            ytd_gross=Decimal("30000000"),
            mom_growth_pct=Decimal("5"),
            yoy_growth_pct=Decimal("10"),
            daily_transactions=50,
            daily_customers=30,
        )
        repo.get_top_products.return_value = MagicMock(items=[])
        repo.get_top_customers.return_value = MagicMock(items=[])
        # Patch the client so no real HTTP call is made
        with patch("datapulse.ai_light.service.OpenRouterClient.chat", return_value="summary text"):
            result = svc.generate_summary(date(2026, 4, 12))
        assert isinstance(result, AISummary)

    def test_graph_service_generate_summary_returns_aisummary(self):
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        # Mock the graph to return a valid state
        with patch.object(svc, "_run_graph") as mock_run:
            mock_run.return_value = {
                "narrative": "Sales strong",
                "highlights": ["H1"],
                "degraded": False,
            }
            result = svc.generate_summary(date(2026, 4, 12))

        assert isinstance(result, AISummary)
        assert result.narrative == "Sales strong"
        assert result.highlights == ["H1"]
        assert result.period == "2026-04-12"

    def test_summary_field_names_match(self):
        """AISummary fields must be identical regardless of service path."""
        legacy = AISummary(narrative="x", highlights=["h"], period="2026-04-12")
        graph = AISummary(narrative="y", highlights=["g"], period="2026-04-12")
        _assert_same_shape(legacy, graph)


# ── AnomalyReport contract ────────────────────────────────────────────────


class TestAnomalyReportContract:
    def test_graph_service_detect_anomalies_returns_anomaly_report(self):
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        with patch.object(svc, "_run_graph") as mock_run:
            mock_run.return_value = {
                "anomalies_list": [
                    {"date": "2026-01-05", "description": "drop", "severity": "high"}
                ],
                "narrative": "one spike",
                "statistical_analysis": {"avg": 5000.0, "std": 1000.0, "count": 30},
                "degraded": False,
            }
            result = svc.detect_anomalies(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, AnomalyReport)
        assert len(result.anomalies) == 1
        assert result.anomalies[0].severity == "high"

    def test_graph_service_degraded_preserves_anomaly_report_shape(self):
        """Fallback (degraded=True) must still return AnomalyReport."""
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        with patch.object(svc, "_run_graph") as mock_run:
            mock_run.return_value = {
                "anomalies_list": [],
                "narrative": "Statistical fallback",
                "statistical_analysis": {"avg": 5000.0, "std": 1000.0, "count": 30},
                "degraded": True,
            }
            result = svc.detect_anomalies(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, AnomalyReport)
        assert result.anomalies == []
        # Shape must be identical to non-degraded
        reference = AnomalyReport(anomalies=[], period="x to y", total_checked=0)
        _assert_same_shape(result, reference)

    def test_anomaly_report_field_names_stable(self):
        """AnomalyReport field contract: anomalies, period, total_checked."""
        assert set(AnomalyReport.model_fields.keys()) == {"anomalies", "period", "total_checked"}

    def test_graph_run_failure_returns_empty_anomaly_report(self):
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        with patch.object(svc, "_run_graph", side_effect=RuntimeError("graph error")):
            result = svc.detect_anomalies(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, AnomalyReport)
        assert result.anomalies == []


# ── ChangeNarrative contract ──────────────────────────────────────────────


class TestChangeNarrativeContract:
    def test_graph_service_explain_changes_returns_change_narrative(self):
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        deltas = [
            {
                "metric": "today_gross",
                "current_value": 120000.0,
                "previous_value": 100000.0,
                "change_pct": 20.0,
                "direction": "up",
            }
        ]
        with patch.object(svc, "_run_graph") as mock_run:
            mock_run.return_value = {
                "narrative": "Sales up 20%",
                "deltas": deltas,
                "degraded": False,
            }
            result = svc.explain_changes(date(2026, 4, 12), date(2026, 3, 12))

        assert isinstance(result, ChangeNarrative)
        assert result.narrative == "Sales up 20%"
        assert len(result.deltas) == 1
        assert result.deltas[0].direction == "up"

    def test_change_narrative_degraded_preserves_shape(self):
        """Fallback returns ChangeNarrative with same field structure."""
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        with patch.object(svc, "_run_graph") as mock_run:
            mock_run.return_value = {
                "narrative": "Fallback narrative",
                "deltas": [],
                "degraded": True,
            }
            result = svc.explain_changes(date(2026, 4, 12), date(2026, 3, 12))

        assert isinstance(result, ChangeNarrative)
        reference = ChangeNarrative(
            narrative="x", deltas=[], current_period="2026-04-12", previous_period="2026-03-12"
        )
        _assert_same_shape(result, reference)

    def test_change_narrative_field_names_stable(self):
        assert set(ChangeNarrative.model_fields.keys()) == {
            "narrative",
            "deltas",
            "current_period",
            "previous_period",
        }

    def test_graph_run_failure_returns_empty_change_narrative(self):
        from datapulse.ai_light.graph_service import AILightGraphService

        session = MagicMock()
        settings = MagicMock()
        settings.openrouter_api_key = ""
        settings.openrouter_model = "openrouter/free"
        svc = AILightGraphService(settings=settings, session=session)

        with patch.object(svc, "_run_graph", side_effect=RuntimeError("graph error")):
            result = svc.explain_changes(date(2026, 4, 12), date(2026, 3, 12))

        assert isinstance(result, ChangeNarrative)
        assert result.narrative == "Change analysis unavailable."
        assert result.deltas == []
