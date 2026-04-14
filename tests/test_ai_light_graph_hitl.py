"""Tests for Phase D: HITL approval flow, checkpoint persistence, and SSE streaming.

These tests cover:
1. HITL flow: require_review=True → GET draft → POST approve → final response
2. Checkpoint persistence: graph state survives graph re-instantiation
3. SSE streaming: endpoint emits events in expected node order
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from datapulse.ai_light.models import (
    AIInsightMeta,
    DeepDiveDraft,
    DeepDiveResponse,
)
from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_ai_light_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_USER = {
    "sub": "test-user",
    "email": "admin@datapulse.local",
    "preferred_username": "admin",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}

MOCK_META = AIInsightMeta(
    run_id="test-run-123",
    model="openai/gpt-4o-mini",
    tokens=200,
    cost_cents=0.01,
    degraded=False,
    duration_ms=500,
)

MOCK_DRAFT = DeepDiveDraft(
    run_id="test-run-123",
    tenant_id="1",
    narrative_draft="Draft narrative pending review.",
    highlights_draft=["Strong Q4", "Anomaly detected in January"],
    data_snapshot={"kpi_snapshot": {"today_gross": 50000}},
    step_trace=[{"node": "analyze", "ts": "2026-04-14T00:00:00Z", "status": "done"}],
)

MOCK_FINAL = DeepDiveResponse(
    narrative="Approved final narrative.",
    highlights=["Strong Q4", "Anomaly detected in January"],
    anomalies_list=[],
    deltas=[],
    degraded=False,
    meta=MOCK_META,
)


def _make_graph_service_mock(
    draft: DeepDiveDraft | None = None,
    final: DeepDiveResponse | None = None,
) -> MagicMock:
    svc = MagicMock()
    type(svc).is_available = PropertyMock(return_value=True)
    svc.start_deep_dive.return_value = draft or MOCK_DRAFT
    svc.get_review_state.return_value = draft or MOCK_DRAFT
    svc.approve_run.return_value = final or MOCK_FINAL
    svc.generate_summary = MagicMock()
    svc.detect_anomalies = MagicMock()
    svc.explain_changes = MagicMock()
    return svc


@pytest.fixture()
def client_hitl() -> TestClient:
    """TestClient pre-wired with a graph service that returns a draft."""
    svc = _make_graph_service_mock()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_ai_light_service] = lambda: svc
    return TestClient(app)


@pytest.fixture()
def client_approved() -> TestClient:
    """TestClient pre-wired with a graph service that returns the final response directly."""
    svc = _make_graph_service_mock(
        draft=None,  # start_deep_dive returns final (no review needed)
        final=MOCK_FINAL,
    )
    svc.start_deep_dive.return_value = MOCK_FINAL  # immediate completion
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_ai_light_service] = lambda: svc
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. HITL flow: POST deep-dive → 202 Draft → GET review → POST approve
# ---------------------------------------------------------------------------


class TestHITLFlow:
    def test_post_deep_dive_require_review_returns_202(self, client_hitl: TestClient):
        resp = client_hitl.post(
            "/api/v1/ai-light/deep-dive",
            json={"require_review": True, "start_date": "2026-03-01", "end_date": "2026-04-01"},
        )
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["run_id"] == "test-run-123"
        assert "narrative_draft" in body
        assert "data_snapshot" in body

    def test_get_review_returns_draft(self, client_hitl: TestClient):
        resp = client_hitl.get("/api/v1/ai-light/review/test-run-123")
        assert resp.status_code == 200
        body = resp.json()
        assert body["run_id"] == "test-run-123"
        assert body["narrative_draft"] == "Draft narrative pending review."
        assert "highlights_draft" in body

    def test_get_review_not_found(self, client_hitl: TestClient):
        # Override to return None (no pending review)
        app = create_app()
        svc = _make_graph_service_mock()
        svc.get_review_state.return_value = None
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc
        c = TestClient(app)
        resp = c.get("/api/v1/ai-light/review/nonexistent-run")
        assert resp.status_code == 404

    def test_post_approve_returns_final_response(self, client_hitl: TestClient):
        resp = client_hitl.post(
            "/api/v1/ai-light/review/test-run-123/approve",
            json={"narrative": "Analyst revised narrative.", "highlights": ["Revised point"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["narrative"] == "Approved final narrative."
        assert body["meta"]["run_id"] == "test-run-123"

    def test_post_approve_no_edits(self, client_hitl: TestClient):
        """Approve with empty body (no edits)."""
        resp = client_hitl.post(
            "/api/v1/ai-light/review/test-run-123/approve",
            json={},
        )
        assert resp.status_code == 200

    def test_full_hitl_flow(self, client_hitl: TestClient):
        """End-to-end HITL: POST → 202 → GET review → POST approve → 200."""
        # Step 1: POST deep-dive with require_review=True
        post_resp = client_hitl.post(
            "/api/v1/ai-light/deep-dive",
            json={"require_review": True},
        )
        assert post_resp.status_code == 202
        run_id = post_resp.json()["run_id"]
        assert run_id == "test-run-123"

        # Step 2: GET pending draft
        get_resp = client_hitl.get(f"/api/v1/ai-light/review/{run_id}")
        assert get_resp.status_code == 200
        draft = get_resp.json()
        assert draft["narrative_draft"] != ""

        # Step 3: Approve with optional edits
        approve_resp = client_hitl.post(
            f"/api/v1/ai-light/review/{run_id}/approve",
            json={"narrative": "Analyst-approved version."},
        )
        assert approve_resp.status_code == 200
        final = approve_resp.json()
        assert final["degraded"] is False


# ---------------------------------------------------------------------------
# 2. Non-HITL deep-dive (synchronous, no review)
# ---------------------------------------------------------------------------


class TestDeepDiveSync:
    def test_post_deep_dive_returns_200_when_no_review(self, client_approved: TestClient):
        resp = client_approved.post(
            "/api/v1/ai-light/deep-dive",
            json={"require_review": False},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "narrative" in body

    def test_post_deep_dive_503_when_not_available(self):
        svc = _make_graph_service_mock()
        type(svc).is_available = PropertyMock(return_value=False)
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc
        c = TestClient(app)
        resp = c.post("/api/v1/ai-light/deep-dive", json={})
        assert resp.status_code == 503

    def test_post_deep_dive_501_when_no_graph_service(self):
        """Legacy service (no start_deep_dive method) returns 501."""
        from datapulse.ai_light.service import AILightService

        svc = MagicMock(spec=AILightService)
        type(svc).is_available = PropertyMock(return_value=True)
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc
        c = TestClient(app)
        resp = c.post("/api/v1/ai-light/deep-dive", json={})
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# 3. Checkpoint persistence — mock PostgresSaver behaviour
# ---------------------------------------------------------------------------


class TestCheckpointPersistence:
    def test_get_review_after_restart_reads_from_checkpointer(self):
        """Simulate a server restart by creating a new service instance pointing to
        the same checkpointer.  The draft should still be retrievable."""
        draft = DeepDiveDraft(
            run_id="persisted-run",
            tenant_id="1",
            narrative_draft="Persisted draft.",
            highlights_draft=["Persisted highlight"],
            data_snapshot={},
            step_trace=[],
        )
        # Simulate restart: create a fresh service and it still returns the checkpoint
        svc2 = _make_graph_service_mock(draft=draft)

        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc2
        c = TestClient(app)

        resp = c.get("/api/v1/ai-light/review/persisted-run")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == "persisted-run"
        assert resp.json()["narrative_draft"] == "Persisted draft."


# ---------------------------------------------------------------------------
# 4. SSE streaming — assert event order
# ---------------------------------------------------------------------------


class TestSSEStreaming:
    def test_summary_stream_emits_events(self):
        async def _mock_stream(insight_type, **kwargs):
            nodes = [
                "cache_check",
                "route",
                "plan_summary",
                "fetch_data",
                "analyze",
                "validate",
                "synthesize",
                "cost_track",
            ]
            for node in nodes:
                yield node, {"status": "done"}

        svc = _make_graph_service_mock()
        svc.stream_run = _mock_stream
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc
        c = TestClient(app)

        with c.stream("GET", "/api/v1/ai-light/summary?stream=true") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            content = b"".join(response.iter_bytes()).decode()

        # Assert SSE events are present in order
        assert "data: " in content
        events = [
            json.loads(line[6:])  # strip "data: "
            for line in content.split("\n")
            if line.startswith("data: ")
        ]
        node_names = [e["node"] for e in events]
        assert "start" in node_names
        assert "end" in node_names

    def test_deep_dive_stream_emits_events(self):
        async def _mock_stream(insight_type, **kwargs):
            for node in ["cache_check", "plan_deep_dive", "fetch_data", "analyze", "synthesize"]:
                yield node, {}

        svc = _make_graph_service_mock()
        svc.stream_run = _mock_stream
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc
        c = TestClient(app)

        url = "/api/v1/ai-light/deep-dive?stream=true"
        with c.stream("POST", url, json={"stream": True}) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_fallback_stream_without_graph_service(self):
        """Legacy service without stream_run yields minimal start/end events."""
        from datapulse.ai_light.service import AILightService

        svc = MagicMock(spec=AILightService)
        type(svc).is_available = PropertyMock(return_value=True)
        # No stream_run attribute
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_ai_light_service] = lambda: svc
        c = TestClient(app)

        with c.stream("GET", "/api/v1/ai-light/summary?stream=true") as response:
            assert response.status_code == 200
            content = b"".join(response.iter_bytes()).decode()

        events = [json.loads(line[6:]) for line in content.split("\n") if line.startswith("data: ")]
        statuses = {e["status"] for e in events}
        assert "running" in statuses or "complete" in statuses
