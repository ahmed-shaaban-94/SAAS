"""Tests for pipeline state machine."""

from __future__ import annotations

import pytest

from datapulse.pipeline.state_machine import (
    ORDERED_STAGES,
    TRANSITIONS,
    InvalidTransitionError,
    PipelineStage,
    get_next_stage,
    get_resume_stage,
    validate_transition,
)


class TestPipelineStage:
    def test_all_stages_have_string_values(self):
        for stage in PipelineStage:
            assert isinstance(stage.value, str)

    def test_ordered_stages_excludes_terminal(self):
        assert PipelineStage.COMPLETED not in ORDERED_STAGES
        assert PipelineStage.FAILED not in ORDERED_STAGES
        assert PipelineStage.PENDING not in ORDERED_STAGES
        assert PipelineStage.RETRYING not in ORDERED_STAGES

    def test_ordered_stages_count(self):
        assert len(ORDERED_STAGES) == 7

    def test_all_stages_have_transitions(self):
        for stage in PipelineStage:
            assert stage in TRANSITIONS


class TestValidateTransition:
    def test_valid_happy_path(self):
        validate_transition(PipelineStage.PENDING, PipelineStage.BRONZE)
        validate_transition(PipelineStage.BRONZE, PipelineStage.QUALITY_BRONZE)
        validate_transition(PipelineStage.QUALITY_BRONZE, PipelineStage.SILVER)
        validate_transition(PipelineStage.SILVER, PipelineStage.QUALITY_SILVER)
        validate_transition(PipelineStage.QUALITY_SILVER, PipelineStage.GOLD)
        validate_transition(PipelineStage.GOLD, PipelineStage.QUALITY_GOLD)
        validate_transition(PipelineStage.QUALITY_GOLD, PipelineStage.FORECASTING)
        validate_transition(PipelineStage.FORECASTING, PipelineStage.COMPLETED)

    def test_any_stage_can_fail(self):
        for stage in [
            PipelineStage.PENDING,
            PipelineStage.BRONZE,
            PipelineStage.SILVER,
            PipelineStage.GOLD,
            PipelineStage.FORECASTING,
        ]:
            validate_transition(stage, PipelineStage.FAILED)

    def test_failed_can_retry(self):
        validate_transition(PipelineStage.FAILED, PipelineStage.RETRYING)

    def test_failed_can_reset_to_pending(self):
        validate_transition(PipelineStage.FAILED, PipelineStage.PENDING)

    def test_completed_cannot_transition(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition(PipelineStage.COMPLETED, PipelineStage.PENDING)

    def test_invalid_backward_transition(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition(PipelineStage.SILVER, PipelineStage.BRONZE)

    def test_invalid_skip_transition(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition(PipelineStage.PENDING, PipelineStage.GOLD)

    def test_error_message_contains_allowed_stages(self):
        with pytest.raises(InvalidTransitionError, match="Allowed"):
            validate_transition(PipelineStage.COMPLETED, PipelineStage.BRONZE)

    def test_retrying_can_go_to_any_execution_stage(self):
        for stage in [
            PipelineStage.BRONZE,
            PipelineStage.SILVER,
            PipelineStage.GOLD,
            PipelineStage.FORECASTING,
        ]:
            validate_transition(PipelineStage.RETRYING, stage)


class TestGetNextStage:
    def test_bronze_next_is_quality_bronze(self):
        assert get_next_stage(PipelineStage.BRONZE) == PipelineStage.QUALITY_BRONZE

    def test_forecasting_next_is_completed(self):
        assert get_next_stage(PipelineStage.FORECASTING) == PipelineStage.COMPLETED

    def test_completed_next_is_none(self):
        assert get_next_stage(PipelineStage.COMPLETED) is None

    def test_failed_next_is_none(self):
        assert get_next_stage(PipelineStage.FAILED) is None

    def test_pending_next_is_none(self):
        assert get_next_stage(PipelineStage.PENDING) is None

    def test_full_happy_path_sequence(self):
        stage = ORDERED_STAGES[0]
        sequence = [stage]
        while True:
            nxt = get_next_stage(stage)
            if nxt is None or nxt == PipelineStage.COMPLETED:
                break
            sequence.append(nxt)
            stage = nxt
        assert len(sequence) == len(ORDERED_STAGES)


class TestGetResumeStage:
    def test_resume_after_bronze(self):
        assert get_resume_stage("bronze") == PipelineStage.QUALITY_BRONZE

    def test_resume_after_quality_silver(self):
        assert get_resume_stage("quality_silver") == PipelineStage.GOLD

    def test_resume_after_forecasting_is_completed(self):
        assert get_resume_stage("forecasting") == PipelineStage.COMPLETED

    def test_resume_with_invalid_stage_returns_none(self):
        assert get_resume_stage("nonexistent") is None

    def test_resume_after_completed_returns_none(self):
        assert get_resume_stage("completed") is None
