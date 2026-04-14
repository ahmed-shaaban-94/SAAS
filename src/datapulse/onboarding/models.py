"""Pydantic models for the onboarding module.

All models are frozen (immutable) to prevent accidental mutation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

ONBOARDING_STEPS: list[str] = [
    "connect_data",
    "first_report",
    "first_goal",
    "configure_first_profile",
]


class OnboardingStatus(BaseModel):
    """Current onboarding progress for a user."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    tenant_id: int
    user_id: str
    steps_completed: list[str] = []
    current_step: str = "connect_data"
    completed_at: datetime | None = None
    skipped_at: datetime | None = None
    created_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete(self) -> bool:
        """True when all onboarding steps have been completed."""
        return all(step in self.steps_completed for step in ONBOARDING_STEPS)


class CompleteStepRequest(BaseModel):
    """Request body for completing a single onboarding step."""

    model_config = ConfigDict(frozen=True)

    step: Literal["connect_data", "first_report", "first_goal", "configure_first_profile"]
