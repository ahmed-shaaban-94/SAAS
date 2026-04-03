"""Pipeline state machine with validated transitions.

Defines the lifecycle of a pipeline run as a directed graph of stages,
and validates that transitions follow the allowed paths.
"""

from __future__ import annotations

from enum import StrEnum


class PipelineStage(StrEnum):
    """Valid stages in a pipeline run lifecycle."""

    PENDING = "pending"
    BRONZE = "bronze"
    QUALITY_BRONZE = "quality_bronze"
    SILVER = "silver"
    QUALITY_SILVER = "quality_silver"
    GOLD = "gold"
    QUALITY_GOLD = "quality_gold"
    FORECASTING = "forecasting"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# Ordered stages for checkpoint/resume logic (excludes terminal states).
ORDERED_STAGES: list[PipelineStage] = [
    PipelineStage.BRONZE,
    PipelineStage.QUALITY_BRONZE,
    PipelineStage.SILVER,
    PipelineStage.QUALITY_SILVER,
    PipelineStage.GOLD,
    PipelineStage.QUALITY_GOLD,
    PipelineStage.FORECASTING,
]


# Valid transitions: from_stage -> set of allowed target stages.
TRANSITIONS: dict[PipelineStage, set[PipelineStage]] = {
    PipelineStage.PENDING: {PipelineStage.BRONZE, PipelineStage.FAILED},
    PipelineStage.BRONZE: {
        PipelineStage.QUALITY_BRONZE,
        PipelineStage.FAILED,
        PipelineStage.RETRYING,
    },
    PipelineStage.QUALITY_BRONZE: {PipelineStage.SILVER, PipelineStage.FAILED},
    PipelineStage.SILVER: {
        PipelineStage.QUALITY_SILVER,
        PipelineStage.FAILED,
        PipelineStage.RETRYING,
    },
    PipelineStage.QUALITY_SILVER: {PipelineStage.GOLD, PipelineStage.FAILED},
    PipelineStage.GOLD: {
        PipelineStage.QUALITY_GOLD,
        PipelineStage.FAILED,
        PipelineStage.RETRYING,
    },
    PipelineStage.QUALITY_GOLD: {
        PipelineStage.FORECASTING,
        PipelineStage.COMPLETED,
        PipelineStage.FAILED,
    },
    PipelineStage.FORECASTING: {
        PipelineStage.COMPLETED,
        PipelineStage.FAILED,
        PipelineStage.RETRYING,
    },
    PipelineStage.RETRYING: {
        PipelineStage.BRONZE,
        PipelineStage.SILVER,
        PipelineStage.GOLD,
        PipelineStage.FORECASTING,
        PipelineStage.FAILED,
    },
    PipelineStage.FAILED: {PipelineStage.RETRYING, PipelineStage.PENDING},
    PipelineStage.COMPLETED: set(),  # terminal
}


class InvalidTransitionError(Exception):
    """Raised when a pipeline stage transition is not allowed."""


def validate_transition(current: PipelineStage, target: PipelineStage) -> None:
    """Validate that a stage transition is allowed.

    Raises:
        InvalidTransitionError: If the transition is not in TRANSITIONS.
    """
    allowed = TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {current.value} to {target.value}. "
            f"Allowed: {sorted(s.value for s in allowed)}"
        )


def get_next_stage(current: PipelineStage) -> PipelineStage | None:
    """Return the next stage in the happy path, or None if terminal."""
    try:
        idx = ORDERED_STAGES.index(current)
    except ValueError:
        return None
    if idx + 1 < len(ORDERED_STAGES):
        return ORDERED_STAGES[idx + 1]
    return PipelineStage.COMPLETED


def get_resume_stage(last_completed: str) -> PipelineStage | None:
    """Given the last completed stage name, return the stage to resume from.

    Returns None if the run was already at the last stage.
    """
    try:
        stage = PipelineStage(last_completed)
    except ValueError:
        return None
    return get_next_stage(stage)
