"""Lead capture service — orchestrates dedup check and insert."""

from __future__ import annotations

from .models import LeadRequest, LeadResponse
from .repository import LeadRepository


class LeadService:
    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    def capture(self, data: LeadRequest) -> LeadResponse:
        if self._repo.email_exists(data.email):
            return LeadResponse(success=True, message="You're already on the list!")
        self._repo.insert(
            email=data.email,
            name=data.name,
            company=data.company,
            use_case=data.use_case,
            team_size=data.team_size,
            tier=data.tier,
        )
        return LeadResponse(success=True, message="You're on the list! We'll be in touch soon.")
