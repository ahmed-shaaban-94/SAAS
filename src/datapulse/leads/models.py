"""Pydantic models for lead capture."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr


class LeadRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: EmailStr
    name: str | None = None
    company: str | None = None
    use_case: str | None = None
    team_size: str | None = None
    tier: str | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    message: str
