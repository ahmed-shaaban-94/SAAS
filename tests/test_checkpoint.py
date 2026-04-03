"""Tests for pipeline checkpoint management."""

from __future__ import annotations

from datapulse.pipeline.checkpoint import (
    build_empty_checkpoint,
    get_completed_stages,
    get_last_successful_stage,
    mark_stage_complete,
    record_retry,
)


class TestBuildEmptyCheckpoint:
    def test_has_required_keys(self):
        cp = build_empty_checkpoint()
        assert cp["last_successful_stage"] is None
        assert cp["completed_stages"] == []
        assert cp["stage_timings"] == {}
        assert cp["retry_history"] == []


class TestMarkStageComplete:
    def test_marks_first_stage(self):
        meta = {}
        result = mark_stage_complete(meta, "bronze", 45.2)
        cp = result["checkpoint"]
        assert cp["last_successful_stage"] == "bronze"
        assert "bronze" in cp["completed_stages"]
        assert cp["stage_timings"]["bronze"]["duration_s"] == 45.2

    def test_marks_subsequent_stage(self):
        meta = mark_stage_complete({}, "bronze", 10.0)
        meta = mark_stage_complete(meta, "quality_bronze", 5.0)
        cp = meta["checkpoint"]
        assert cp["last_successful_stage"] == "quality_bronze"
        assert cp["completed_stages"] == ["bronze", "quality_bronze"]

    def test_does_not_mutate_input(self):
        original = {"existing_key": "value"}
        result = mark_stage_complete(original, "bronze", 10.0)
        assert "checkpoint" not in original
        assert "checkpoint" in result
        assert result["existing_key"] == "value"

    def test_does_not_duplicate_stages(self):
        meta = mark_stage_complete({}, "bronze", 10.0)
        meta = mark_stage_complete(meta, "bronze", 12.0)
        cp = meta["checkpoint"]
        assert cp["completed_stages"].count("bronze") == 1
        assert cp["stage_timings"]["bronze"]["duration_s"] == 12.0

    def test_preserves_existing_metadata(self):
        meta = {"source_dir": "/data", "tenant_id": 1}
        result = mark_stage_complete(meta, "bronze", 10.0)
        assert result["source_dir"] == "/data"
        assert result["tenant_id"] == 1


class TestRecordRetry:
    def test_records_single_retry(self):
        meta = {}
        result = record_retry(meta, "silver", 1, "connection timeout")
        cp = result["checkpoint"]
        assert len(cp["retry_history"]) == 1
        entry = cp["retry_history"][0]
        assert entry["stage"] == "silver"
        assert entry["attempt"] == 1
        assert entry["error"] == "connection timeout"
        assert "timestamp" in entry

    def test_accumulates_retries(self):
        meta = record_retry({}, "silver", 1, "error 1")
        meta = record_retry(meta, "silver", 2, "error 2")
        meta = record_retry(meta, "silver", 3, "error 3")
        cp = meta["checkpoint"]
        assert len(cp["retry_history"]) == 3

    def test_truncates_long_error(self):
        long_error = "x" * 500
        result = record_retry({}, "bronze", 1, long_error)
        entry = result["checkpoint"]["retry_history"][0]
        assert len(entry["error"]) == 200

    def test_does_not_mutate_input(self):
        original = {}
        result = record_retry(original, "bronze", 1, "error")
        assert "checkpoint" not in original
        assert "checkpoint" in result


class TestGetLastSuccessfulStage:
    def test_returns_none_for_empty_metadata(self):
        assert get_last_successful_stage({}) is None

    def test_returns_none_for_no_checkpoint(self):
        assert get_last_successful_stage({"other": "data"}) is None

    def test_returns_stage_when_set(self):
        meta = mark_stage_complete({}, "silver", 10.0)
        assert get_last_successful_stage(meta) == "silver"


class TestGetCompletedStages:
    def test_returns_empty_for_no_checkpoint(self):
        assert get_completed_stages({}) == []

    def test_returns_completed_list(self):
        meta = mark_stage_complete({}, "bronze", 10.0)
        meta = mark_stage_complete(meta, "quality_bronze", 5.0)
        assert get_completed_stages(meta) == ["bronze", "quality_bronze"]

    def test_returns_copy_not_reference(self):
        meta = mark_stage_complete({}, "bronze", 10.0)
        stages1 = get_completed_stages(meta)
        stages2 = get_completed_stages(meta)
        stages1.append("modified")
        assert "modified" not in stages2
