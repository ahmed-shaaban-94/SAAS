"""Tests for AILightState TypedDict and step_trace append reducer."""

from __future__ import annotations

from datapulse.ai_light.graph.state import AILightState, _append_reducer


class TestAppendReducer:
    """Unit tests for the step_trace custom reducer."""

    def test_both_none(self):
        result = _append_reducer(None, None)
        assert result == []

    def test_existing_none(self):
        new = [{"node": "a"}]
        result = _append_reducer(None, new)
        assert result == [{"node": "a"}]

    def test_new_none(self):
        existing = [{"node": "a"}]
        result = _append_reducer(existing, None)
        assert result == [{"node": "a"}]

    def test_both_populated(self):
        existing = [{"node": "a"}]
        new = [{"node": "b"}, {"node": "c"}]
        result = _append_reducer(existing, new)
        assert result == [{"node": "a"}, {"node": "b"}, {"node": "c"}]

    def test_does_not_mutate_existing(self):
        existing = [{"node": "a"}]
        original_id = id(existing)
        result = _append_reducer(existing, [{"node": "b"}])
        # result is a new list
        assert id(result) != original_id
        # original unchanged
        assert existing == [{"node": "a"}]

    def test_empty_new(self):
        existing = [{"node": "x"}]
        result = _append_reducer(existing, [])
        assert result == [{"node": "x"}]

    def test_empty_existing(self):
        result = _append_reducer([], [{"node": "y"}])
        assert result == [{"node": "y"}]


class TestAILightState:
    """TypedDict structural tests."""

    def test_minimal_state(self):
        state: AILightState = {
            "insight_type": "summary",
            "tenant_id": "1",
            "run_id": "abc-123",
        }
        assert state["insight_type"] == "summary"

    def test_optional_keys_absent(self):
        state: AILightState = {}
        assert state.get("narrative") is None
        assert state.get("cache_hit") is None

    def test_full_state_construction(self):
        state: AILightState = {
            "tenant_id": "1",
            "run_id": "uuid-here",
            "insight_type": "summary",
            "target_date": "2026-04-12",
            "params_hash": "abc",
            "cache_hit": False,
            "validation_retries": 0,
            "circuit_breaker_failures": 0,
            "degraded": False,
            "step_trace": [],
            "cost_cents": 0.0,
        }
        assert state["tenant_id"] == "1"
        assert state["degraded"] is False

    def test_degraded_default_absent(self):
        state: AILightState = {}
        # TypedDict allows missing keys; .get returns None
        assert state.get("degraded") is None
