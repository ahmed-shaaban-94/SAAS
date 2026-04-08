"""Pydantic models for gamification: badges, XP, streaks, competitions."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


# ------------------------------------------------------------------
# Badge models
# ------------------------------------------------------------------

class BadgeResponse(BaseModel):
    """A badge definition."""

    model_config = ConfigDict(frozen=True)

    badge_id: int
    badge_key: str
    title_en: str
    title_ar: str | None = None
    description_en: str = ""
    description_ar: str | None = None
    icon: str = "trophy"
    tier: str = "bronze"
    category: str = "sales"
    is_active: bool = True


class StaffBadgeResponse(BaseModel):
    """A badge earned by a staff member."""

    model_config = ConfigDict(frozen=True)

    badge_id: int
    badge_key: str
    title_en: str
    title_ar: str | None = None
    icon: str
    tier: str
    category: str
    earned_at: datetime
    context: dict = Field(default_factory=dict)


# ------------------------------------------------------------------
# Streak models
# ------------------------------------------------------------------

class StreakResponse(BaseModel):
    """Current streak status for a staff member."""

    model_config = ConfigDict(frozen=True)

    streak_type: str
    current_count: int = 0
    best_count: int = 0
    last_date: date | None = None


# ------------------------------------------------------------------
# XP & Level models
# ------------------------------------------------------------------

class XPEvent(BaseModel):
    """Single XP transaction."""

    model_config = ConfigDict(frozen=True)

    id: int
    xp_amount: int
    source: str
    source_ref: str | None = None
    earned_at: datetime


class StaffLevelResponse(BaseModel):
    """Staff member's current level and XP."""

    model_config = ConfigDict(frozen=True)

    staff_key: int
    level: int = 1
    total_xp: int = 0
    current_tier: str = "bronze"
    xp_to_next_level: int = 0


class GamificationProfile(BaseModel):
    """Full gamification profile for a staff member."""

    model_config = ConfigDict(frozen=True)

    staff_key: int
    staff_name: str = ""
    level: int = 1
    total_xp: int = 0
    current_tier: str = "bronze"
    xp_to_next_level: int = 0
    badges: list[StaffBadgeResponse] = Field(default_factory=list)
    streaks: list[StreakResponse] = Field(default_factory=list)
    badge_count: int = 0


# ------------------------------------------------------------------
# Competition models
# ------------------------------------------------------------------

class CompetitionCreate(BaseModel):
    """Input model for creating a competition."""

    title: str
    description: str = ""
    competition_type: str = "individual"
    metric: str = "revenue"
    start_date: date
    end_date: date
    prize_description: str | None = None


class CompetitionResponse(BaseModel):
    """A competition definition."""

    model_config = ConfigDict(frozen=True)

    competition_id: int
    title: str
    description: str = ""
    competition_type: str
    metric: str
    start_date: date
    end_date: date
    status: str
    prize_description: str | None = None
    created_at: datetime


class CompetitionEntryResponse(BaseModel):
    """A participant in a competition."""

    model_config = ConfigDict(frozen=True)

    staff_key: int
    staff_name: str = ""
    score: JsonDecimal
    rank: int | None = None


class CompetitionDetail(BaseModel):
    """Competition with its leaderboard entries."""

    model_config = ConfigDict(frozen=True)

    competition: CompetitionResponse
    entries: list[CompetitionEntryResponse] = Field(default_factory=list)


# ------------------------------------------------------------------
# Leaderboard models
# ------------------------------------------------------------------

class LeaderboardEntry(BaseModel):
    """Entry in the XP leaderboard."""

    model_config = ConfigDict(frozen=True)

    rank: int
    staff_key: int
    staff_name: str = ""
    level: int = 1
    total_xp: int = 0
    current_tier: str = "bronze"
    badge_count: int = 0


# ------------------------------------------------------------------
# Activity feed
# ------------------------------------------------------------------

class FeedItem(BaseModel):
    """A single gamification activity event."""

    model_config = ConfigDict(frozen=True)

    id: int
    staff_key: int
    staff_name: str = ""
    event_type: str
    title: str
    description: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
