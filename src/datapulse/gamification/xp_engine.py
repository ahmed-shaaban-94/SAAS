"""XP calculation engine — maps events to experience points."""

from __future__ import annotations

# XP rewards per source type
XP_TABLE: dict[str, int] = {
    "sale": 10,
    "large_sale": 50,  # sale > 10k
    "daily_target_hit": 100,
    "monthly_target_hit": 500,
    "streak_bonus_7": 200,
    "streak_bonus_30": 1000,
    "streak_bonus_90": 5000,
    "badge_earned": 150,
    "competition_win": 2000,
    "competition_top3": 1000,
    "new_customer": 25,
    "zero_returns_day": 50,
}

# Level thresholds: level N requires this much *cumulative* XP.
# Formula: XP = 1000 * (level ^ 1.5)  — logarithmic growth
_LEVEL_CAP = 100


def xp_for_level(level: int) -> int:
    """Return cumulative XP required to reach a given level."""
    if level <= 1:
        return 0
    return int(1000 * (level**1.5))


def level_from_xp(total_xp: int) -> int:
    """Derive level from total XP."""
    level = 1
    while level < _LEVEL_CAP and total_xp >= xp_for_level(level + 1):
        level += 1
    return level


def xp_to_next(total_xp: int) -> int:
    """Return how many XP are needed to reach the next level."""
    current_level = level_from_xp(total_xp)
    if current_level >= _LEVEL_CAP:
        return 0
    return xp_for_level(current_level + 1) - total_xp


def tier_from_level(level: int) -> str:
    """Map level to tier name."""
    if level >= 80:
        return "diamond"
    if level >= 50:
        return "platinum"
    if level >= 30:
        return "gold"
    if level >= 15:
        return "silver"
    return "bronze"


def get_xp_for_source(source: str) -> int:
    """Look up XP value for a given source type."""
    return XP_TABLE.get(source, 0)


def streak_multiplier(streak_count: int) -> float:
    """Bonus multiplier based on active streak length."""
    if streak_count >= 30:
        return 2.0
    if streak_count >= 14:
        return 1.5
    if streak_count >= 7:
        return 1.25
    return 1.0
