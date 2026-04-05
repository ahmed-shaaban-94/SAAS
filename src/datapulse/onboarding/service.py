"""Business logic layer for onboarding wizard."""

from __future__ import annotations

from datetime import UTC, datetime

from datapulse.logging import get_logger
from datapulse.onboarding.models import ONBOARDING_STEPS, OnboardingStatus
from datapulse.onboarding.repository import OnboardingRepository

log = get_logger(__name__)


class OnboardingService:
    """Orchestrates onboarding progress operations."""

    def __init__(self, repo: OnboardingRepository) -> None:
        self._repo = repo

    def get_status(self, tenant_id: int, user_id: str) -> OnboardingStatus:
        """Return current onboarding status, or a fresh default if no row exists."""
        log.info("service_get_onboarding", user_id=user_id)
        row = self._repo.get_status(user_id)
        if row is None:
            return OnboardingStatus(tenant_id=tenant_id, user_id=user_id)
        return OnboardingStatus(**row)

    def complete_step(self, tenant_id: int, user_id: str, step: str) -> OnboardingStatus:
        """Mark a step as completed and advance to the next step.

        If all steps are done, sets completed_at timestamp.
        """
        log.info("service_complete_step", user_id=user_id, step=step)

        if step not in ONBOARDING_STEPS:
            raise ValueError(f"Invalid step: {step}. Must be one of {ONBOARDING_STEPS}")

        # Get current state (or defaults for a fresh user)
        current = self.get_status(tenant_id, user_id)
        steps_completed = list(current.steps_completed)

        # Add step if not already completed
        if step not in steps_completed:
            steps_completed.append(step)

        # Determine next step: first incomplete step, or last step if all done
        current_step = step
        for s in ONBOARDING_STEPS:
            if s not in steps_completed:
                current_step = s
                break
        else:
            # All steps completed — keep the last step as current
            current_step = ONBOARDING_STEPS[-1]

        # Set completed_at if all steps are done
        all_done = all(s in steps_completed for s in ONBOARDING_STEPS)
        completed_at = datetime.now(UTC) if all_done else current.completed_at

        row = self._repo.upsert_status(
            tenant_id=tenant_id,
            user_id=user_id,
            steps_completed=steps_completed,
            current_step=current_step,
            completed_at=completed_at,
            skipped_at=current.skipped_at,
        )
        return OnboardingStatus(**row)

    def skip(self, tenant_id: int, user_id: str) -> OnboardingStatus:
        """Skip the onboarding wizard entirely."""
        log.info("service_skip_onboarding", user_id=user_id)
        current = self.get_status(tenant_id, user_id)

        row = self._repo.upsert_status(
            tenant_id=tenant_id,
            user_id=user_id,
            steps_completed=list(current.steps_completed),
            current_step=current.current_step,
            completed_at=current.completed_at,
            skipped_at=datetime.now(UTC),
        )
        return OnboardingStatus(**row)
