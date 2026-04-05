"""Tests for the AI-Light module (Phase 2.8)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from datapulse.ai_light.client import OpenRouterClient
from datapulse.ai_light.models import (
    AISummary,
    Anomaly,
    AnomalyReport,
    ChangeDelta,
    ChangeNarrative,
    InsightRequest,
)
from datapulse.ai_light.service import AILightService

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_insight_request(self):
        req = InsightRequest(insight_type="summary")
        assert req.insight_type == "summary"
        assert req.start_date is None

    def test_ai_summary(self):
        s = AISummary(narrative="Test", highlights=["a", "b"], period="2025-01-01")
        assert s.narrative == "Test"
        assert len(s.highlights) == 2

    def test_anomaly(self):
        a = Anomaly(
            date="2025-01-01",
            metric="daily_net_sales",
            actual_value=Decimal("1000"),
            expected_range_low=Decimal("500"),
            expected_range_high=Decimal("800"),
            severity="high",
            description="Unusual spike",
        )
        assert a.severity == "high"
        # JSON serialization should produce float
        data = a.model_dump()
        assert isinstance(data["actual_value"], float)

    def test_anomaly_report(self):
        report = AnomalyReport(anomalies=[], period="2025-01 to 2025-02", total_checked=30)
        assert report.total_checked == 30
        assert len(report.anomalies) == 0

    def test_change_delta(self):
        d = ChangeDelta(
            metric="Net Sales",
            previous_value=Decimal("100"),
            current_value=Decimal("120"),
            change_pct=Decimal("20"),
            direction="up",
        )
        assert d.direction == "up"

    def test_change_narrative(self):
        n = ChangeNarrative(
            narrative="Revenue increased.",
            deltas=[],
            current_period="2025-02",
            previous_period="2025-01",
        )
        assert n.narrative == "Revenue increased."


# ---------------------------------------------------------------------------
# Client tests
# ---------------------------------------------------------------------------


class TestOpenRouterClient:
    def _make_client(self, api_key: str = "test-key") -> OpenRouterClient:
        settings = MagicMock()
        settings.openrouter_api_key = api_key
        settings.openrouter_model = "test-model"
        return OpenRouterClient(settings)

    def test_is_configured_true(self):
        client = self._make_client("sk-test")
        assert client.is_configured is True

    def test_is_configured_false(self):
        client = self._make_client("")
        assert client.is_configured is False

    def test_chat_raises_without_key(self):
        client = self._make_client("")
        with pytest.raises(RuntimeError, match="not configured"):
            client.chat("system", "user")

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"total_tokens": 50},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = self._make_client("sk-test")
        result = client.chat("system", "user")
        assert result == "Hello!"
        mock_post.assert_called_once()

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_json_parses_array(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '[{"date": "2025-01-01"}]'}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = self._make_client("sk-test")
        result = client.chat_json("system", "user")
        assert isinstance(result, list)
        assert result[0]["date"] == "2025-01-01"

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_json_strips_code_fences(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "```json\n[]\n```"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = self._make_client("sk-test")
        result = client.chat_json("system", "user")
        assert result == []


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


def _mock_kpi(today=1000, mtd=10000, ytd=100000, mom=5.0, yoy=10.0, txns=50, cust=30):
    from datapulse.analytics.models import KPISummary

    return KPISummary(
        today_gross=Decimal(str(today)),
        mtd_gross=Decimal(str(mtd)),
        ytd_gross=Decimal(str(ytd)),
        mom_growth_pct=Decimal(str(mom)),
        yoy_growth_pct=Decimal(str(yoy)),
        daily_transactions=txns,
        daily_customers=cust,
    )


def _mock_ranking(items_data=None):
    from datapulse.analytics.models import RankingItem, RankingResult

    if items_data is None:
        items_data = [("Product A", 5000), ("Product B", 3000)]
    items = [
        RankingItem(
            rank=i + 1,
            key=i + 1,
            name=name,
            value=Decimal(str(val)),
            pct_of_total=Decimal("50"),
        )
        for i, (name, val) in enumerate(items_data)
    ]
    return RankingResult(items=items, total=Decimal("10000"))


def _mock_trend(values=None):
    from datapulse.analytics.models import TimeSeriesPoint, TrendResult

    if values is None:
        values = [100, 200, 300, 150, 500, 180, 190, 210, 195, 185]
    points = [
        TimeSeriesPoint(period=f"2025-01-{i + 1:02d}", value=Decimal(str(v)))
        for i, v in enumerate(values)
    ]
    if not values:
        return TrendResult(
            points=[],
            total=Decimal("0"),
            average=Decimal("0"),
            minimum=Decimal("0"),
            maximum=Decimal("0"),
            growth_pct=None,
        )
    total = sum(values)
    return TrendResult(
        points=points,
        total=Decimal(str(total)),
        average=Decimal(str(total / len(values))),
        minimum=Decimal(str(min(values))),
        maximum=Decimal(str(max(values))),
        growth_pct=Decimal("10"),
    )


class TestAILightService:
    def _make_service(self, api_key: str = "") -> tuple[AILightService, MagicMock, MagicMock]:
        settings = MagicMock()
        settings.openrouter_api_key = api_key
        settings.openrouter_model = "test-model"
        session = MagicMock()

        svc = AILightService(settings, session)
        # Mock the repo
        svc._repo = MagicMock()
        return svc, svc._repo, svc._client

    def test_is_available_false(self):
        svc, _, _ = self._make_service("")
        assert svc.is_available is False

    def test_is_available_true(self):
        svc, _, _ = self._make_service("sk-test")
        assert svc.is_available is True

    @patch("datapulse.ai_light.client.httpx.post")
    def test_generate_summary(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Revenue is up.\n- Highlight 1\n- Highlight 2"}}],
            "usage": {"total_tokens": 100},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc, repo, _ = self._make_service("sk-test")
        repo.get_kpi_summary.return_value = _mock_kpi()
        repo.get_top_products.return_value = _mock_ranking()
        repo.get_top_customers.return_value = _mock_ranking()

        result = svc.generate_summary(date(2025, 1, 15))
        assert isinstance(result, AISummary)
        assert result.period == "2025-01-15"
        assert len(result.highlights) >= 1

    def test_detect_anomalies_statistical_only(self):
        """Anomaly detection works without OpenRouter (statistical fallback)."""
        svc, repo, _ = self._make_service("")  # No API key
        # Create data with one big spike
        values = [100, 105, 98, 102, 100, 95, 103, 99, 101, 500]
        repo.get_daily_trend.return_value = _mock_trend(values)

        result = svc.detect_anomalies(date(2025, 1, 1), date(2025, 1, 10))
        assert isinstance(result, AnomalyReport)
        assert result.total_checked == 10
        # The spike at 500 should be detected
        assert len(result.anomalies) >= 1
        spike = result.anomalies[0]
        assert "spike" in spike.description.lower() or float(spike.actual_value) > 400

    def test_detect_anomalies_no_data(self):
        svc, repo, _ = self._make_service("")
        repo.get_daily_trend.return_value = _mock_trend([])

        result = svc.detect_anomalies()
        assert result.total_checked == 0
        assert len(result.anomalies) == 0

    def test_detect_anomalies_few_points(self):
        svc, repo, _ = self._make_service("")
        repo.get_daily_trend.return_value = _mock_trend([100, 200])

        result = svc.detect_anomalies()
        assert result.total_checked == 2

    def test_explain_changes_without_ai(self):
        """Change narrative works as fallback without OpenRouter."""
        svc, repo, _ = self._make_service("")
        repo.get_kpi_summary.side_effect = [
            _mock_kpi(today=1200, mtd=12000, ytd=120000, txns=60, cust=35),
            _mock_kpi(today=1000, mtd=10000, ytd=100000, txns=50, cust=30),
        ]

        result = svc.explain_changes(date(2025, 2, 1), date(2025, 1, 1))
        assert isinstance(result, ChangeNarrative)
        assert len(result.deltas) == 5
        assert result.current_period == "2025-02-01"
        assert result.previous_period == "2025-01-01"
        # Daily Net Sales went up
        net_delta = result.deltas[0]
        assert net_delta.direction == "up"

    @patch("datapulse.ai_light.client.httpx.post")
    def test_explain_changes_with_ai(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Revenue increased 20% driven by new products."}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc, repo, _ = self._make_service("sk-test")
        repo.get_kpi_summary.side_effect = [
            _mock_kpi(today=1200),
            _mock_kpi(today=1000),
        ]

        result = svc.explain_changes(date(2025, 2, 1), date(2025, 1, 1))
        assert "Revenue" in result.narrative

    def test_build_change_narrative_text(self):
        deltas = [
            ChangeDelta(
                metric="Net Sales",
                previous_value=Decimal("100"),
                current_value=Decimal("120"),
                change_pct=Decimal("20"),
                direction="up",
            ),
        ]
        text = AILightService._build_change_narrative_text(deltas)
        assert "Net Sales" in text
        assert "up" in text


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestAILightEndpoints:
    @pytest.fixture
    def mock_svc(self):
        return MagicMock()

    @pytest.fixture
    def client(self, mock_svc):
        from fastapi.testclient import TestClient

        from datapulse.api import deps
        from datapulse.api.app import create_app
        from datapulse.api.auth import get_current_user
        from datapulse.api.deps import get_ai_light_service

        _dev_user = {
            "sub": "test-user",
            "email": "test@datapulse.local",
            "preferred_username": "test",
            "tenant_id": "1",
            "roles": ["admin"],
            "raw_claims": {},
        }

        app = create_app()
        app.dependency_overrides[get_ai_light_service] = lambda: mock_svc
        app.dependency_overrides[deps.get_db_session] = lambda: MagicMock()
        app.dependency_overrides[deps.get_tenant_session] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: _dev_user
        yield TestClient(app, headers={"X-API-Key": "test-api-key"})
        app.dependency_overrides.clear()

    def test_status_endpoint(self, mock_svc, client):
        mock_svc.is_available = True
        resp = client.get("/api/v1/ai-light/status")
        assert resp.status_code == 200
        assert resp.json()["available"] is True

    def test_summary_returns_503_when_unavailable(self, mock_svc, client):
        mock_svc.is_available = False
        resp = client.get("/api/v1/ai-light/summary")
        assert resp.status_code == 503

    def test_anomalies_endpoint(self, mock_svc, client):
        mock_svc.detect_anomalies.return_value = AnomalyReport(
            anomalies=[], period="2025-01", total_checked=30
        )
        resp = client.get("/api/v1/ai-light/anomalies")
        assert resp.status_code == 200
        assert resp.json()["total_checked"] == 30

    def test_changes_endpoint(self, mock_svc, client):
        mock_svc.explain_changes.return_value = ChangeNarrative(
            narrative="Test",
            deltas=[],
            current_period="2025-02",
            previous_period="2025-01",
        )
        resp = client.get("/api/v1/ai-light/changes")
        assert resp.status_code == 200
        assert resp.json()["narrative"] == "Test"
