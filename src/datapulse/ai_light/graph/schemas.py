"""Pydantic validation schemas for LangGraph AI-Light node outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SummaryOutput(BaseModel):
    """Validated output schema for the summary insight type."""

    narrative: str = Field(min_length=10, description="Executive narrative paragraph")
    highlights: list[str] = Field(min_length=1, description="Bullet-point highlights")

    @field_validator("highlights")
    @classmethod
    def _non_empty_items(cls, v: list[str]) -> list[str]:
        cleaned = [item.strip() for item in v if item.strip()]
        if not cleaned:
            raise ValueError("highlights list must contain at least one non-empty string")
        return cleaned

    @field_validator("narrative")
    @classmethod
    def _no_placeholder(cls, v: str) -> str:
        if v.strip().lower() in {"n/a", "none", "null", ""}:
            raise ValueError("narrative must not be a placeholder")
        return v.strip()
