"""Lead capture repository — raw SQL, no business logic."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def email_exists(self, email: str) -> bool:
        row = (
            await self._session.execute(
                text("SELECT 1 FROM public.leads WHERE email = :email LIMIT 1"),
                {"email": email},
            )
        ).fetchone()
        return row is not None

    async def insert(
        self,
        email: str,
        name: str | None,
        company: str | None,
        use_case: str | None,
        team_size: str | None,
        tier: str | None,
    ) -> None:
        await self._session.execute(
            text("""
                INSERT INTO public.leads (email, name, company, use_case, team_size, tier)
                VALUES (:email, :name, :company, :use_case, :team_size, :tier)
                ON CONFLICT (email) DO NOTHING
            """),
            {
                "email": email,
                "name": name,
                "company": company,
                "use_case": use_case,
                "team_size": team_size,
                "tier": tier,
            },
        )
