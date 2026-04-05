"""Repository for onboarding progress — raw SQL via SQLAlchemy text().

All queries use parameterized placeholders to prevent SQL injection.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class OnboardingRepository:
    """Data-access layer for onboarding progress tracking."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_status(self, user_id: str) -> dict | None:
        """Fetch onboarding status for a user. Returns None if no row exists."""
        log.info("get_onboarding_status", user_id=user_id)
        stmt = text("""
            SELECT id, tenant_id, user_id, steps_completed, current_step,
                   completed_at, skipped_at, created_at
            FROM public.onboarding
            WHERE user_id = :user_id
        """)
        row = self._session.execute(stmt, {"user_id": user_id}).mappings().fetchone()
        if row is None:
            return None
        return dict(row)

    def upsert_status(
        self,
        tenant_id: int,
        user_id: str,
        steps_completed: list[str],
        current_step: str,
        completed_at: datetime | None,
        skipped_at: datetime | None,
    ) -> dict:
        """Insert or update onboarding status. Returns the upserted row."""
        log.info(
            "upsert_onboarding_status",
            tenant_id=tenant_id,
            user_id=user_id,
            current_step=current_step,
            steps_completed=steps_completed,
        )
        stmt = text("""
            INSERT INTO public.onboarding
                (tenant_id, user_id, steps_completed, current_step,
                 completed_at, skipped_at, created_at)
            VALUES
                (:tenant_id, :user_id, :steps_completed, :current_step,
                 :completed_at, :skipped_at, now())
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET
                steps_completed = :steps_completed,
                current_step    = :current_step,
                completed_at    = :completed_at,
                skipped_at      = :skipped_at
            RETURNING id, tenant_id, user_id, steps_completed, current_step,
                      completed_at, skipped_at, created_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "steps_completed": steps_completed,
                    "current_step": current_step,
                    "completed_at": completed_at,
                    "skipped_at": skipped_at,
                },
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            raise RuntimeError("UPSERT RETURNING unexpectedly returned no row")
        return dict(row)
