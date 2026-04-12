"""Business logic layer for gamification."""

from __future__ import annotations

from datetime import date

from datapulse.gamification.badge_rules import StaffMetrics, evaluate_badges
from datapulse.gamification.models import (
    BadgeResponse,
    CompetitionCreate,
    CompetitionDetail,
    CompetitionResponse,
    FeedItem,
    GamificationProfile,
    LeaderboardEntry,
    StaffBadgeResponse,
    StaffLevelResponse,
    StreakResponse,
    XPEvent,
)
from datapulse.gamification.repository import GamificationRepository
from datapulse.gamification.xp_engine import (
    get_xp_for_source,
    level_from_xp,
    tier_from_level,
    xp_to_next,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class GamificationService:
    """Orchestrates gamification operations."""

    def __init__(self, repo: GamificationRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, staff_key: int) -> GamificationProfile:
        """Build full gamification profile for a staff member."""
        log.info("get_gamification_profile", staff_key=staff_key)
        level_info = self._repo.get_staff_level(staff_key)
        badges = self._repo.get_staff_badges(staff_key)
        streaks = self._repo.get_streaks(staff_key)

        if level_info is None:
            return GamificationProfile(
                staff_key=staff_key,
                badges=badges,
                streaks=streaks,
                badge_count=len(badges),
            )

        return GamificationProfile(
            staff_key=staff_key,
            level=level_info.level,
            total_xp=level_info.total_xp,
            current_tier=level_info.current_tier,
            xp_to_next_level=level_info.xp_to_next_level,
            badges=badges,
            streaks=streaks,
            badge_count=len(badges),
        )

    # ------------------------------------------------------------------
    # Badges
    # ------------------------------------------------------------------

    def list_badges(self) -> list[BadgeResponse]:
        """Return all available badges."""
        return self._repo.list_badges()

    def get_staff_badges(self, staff_key: int) -> list[StaffBadgeResponse]:
        """Return badges earned by a staff member."""
        return self._repo.get_staff_badges(staff_key)

    def award_badge(self, staff_key: int, badge_key: str, context: dict | None = None) -> bool:
        """Manually award a badge. Returns True if newly awarded."""
        awarded = self._repo.award_badge(staff_key, badge_key, context)
        if awarded:
            log.info("badge_manually_awarded", staff_key=staff_key, badge_key=badge_key)
        return awarded

    def evaluate_and_award(self, metrics: StaffMetrics) -> list[str]:
        """Evaluate badge rules and award any newly earned badges.

        Returns list of newly awarded badge keys.
        """
        already = self._repo.get_earned_badge_keys(metrics.staff_key)
        newly_earned = evaluate_badges(metrics, already)

        for badge_key in newly_earned:
            awarded = self._repo.award_badge(metrics.staff_key, badge_key)
            if awarded:
                log.info("badge_awarded", staff_key=metrics.staff_key, badge_key=badge_key)
                self._repo.add_feed_event(
                    staff_key=metrics.staff_key,
                    event_type="badge_earned",
                    title=f"Earned badge: {badge_key}",
                    metadata={"badge_key": badge_key},
                )
                self.grant_xp(metrics.staff_key, "badge_earned", source_ref=badge_key)

        return newly_earned

    # ------------------------------------------------------------------
    # Streaks
    # ------------------------------------------------------------------

    def get_streaks(self, staff_key: int) -> list[StreakResponse]:
        """Return current streaks for a staff member."""
        return self._repo.get_streaks(staff_key)

    def record_streak(
        self,
        staff_key: int,
        streak_type: str,
        today: date | None = None,
    ) -> StreakResponse:
        """Update a streak for today."""
        today = today or date.today()
        streak = self._repo.update_streak(staff_key, streak_type, today)

        # Check for streak milestones
        for milestone in [7, 30, 90]:
            if streak.current_count == milestone:
                source = f"streak_bonus_{milestone}"
                self.grant_xp(staff_key, source, source_ref=streak_type)
                self._repo.add_feed_event(
                    staff_key=staff_key,
                    event_type="streak_milestone",
                    title=f"{milestone}-day streak!",
                    metadata={"streak_type": streak_type, "count": milestone},
                )
                log.info("streak_milestone", staff_key=staff_key, milestone=milestone)

        return streak

    # ------------------------------------------------------------------
    # XP & Levels
    # ------------------------------------------------------------------

    def grant_xp(
        self,
        staff_key: int,
        source: str,
        source_ref: str | None = None,
    ) -> StaffLevelResponse:
        """Grant XP to a staff member and recalculate level."""
        xp_amount = get_xp_for_source(source)
        if xp_amount <= 0:
            level_info = self._repo.get_staff_level(staff_key)
            if level_info:
                return level_info
            return StaffLevelResponse(staff_key=staff_key)

        self._repo.add_xp(staff_key, xp_amount, source, source_ref)
        total = self._repo.get_total_xp(staff_key)
        new_level = level_from_xp(total)
        new_tier = tier_from_level(new_level)

        # Check for level-up
        old_level_info = self._repo.get_staff_level(staff_key)
        old_level = old_level_info.level if old_level_info else 0

        self._repo.upsert_level(staff_key, new_level, total, new_tier)

        if new_level > old_level and old_level > 0:
            log.info("level_up", staff_key=staff_key, old_level=old_level, new_level=new_level)
            self._repo.add_feed_event(
                staff_key=staff_key,
                event_type="level_up",
                title=f"Level up! Now level {new_level}",
                metadata={"old_level": old_level, "new_level": new_level, "tier": new_tier},
            )

        return StaffLevelResponse(
            staff_key=staff_key,
            level=new_level,
            total_xp=total,
            current_tier=new_tier,
            xp_to_next_level=xp_to_next(total),
        )

    def get_xp_history(self, staff_key: int, limit: int = 50) -> list[XPEvent]:
        """Return recent XP events."""
        return self._repo.get_xp_history(staff_key, limit)

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_leaderboard(self, limit: int = 20) -> list[LeaderboardEntry]:
        """Return XP leaderboard."""
        return self._repo.get_leaderboard(limit)

    # ------------------------------------------------------------------
    # Competitions
    # ------------------------------------------------------------------

    def create_competition(self, data: CompetitionCreate, created_by: str) -> CompetitionResponse:
        """Create a new competition."""
        log.info("create_competition", title=data.title)
        return self._repo.create_competition(data, created_by)

    def list_competitions(self, status: str | None = None) -> list[CompetitionResponse]:
        """List competitions."""
        return self._repo.list_competitions(status)

    def get_competition_detail(self, competition_id: int) -> CompetitionDetail:
        """Get competition with its leaderboard."""
        competitions = self._repo.list_competitions()
        comp = next((c for c in competitions if c.competition_id == competition_id), None)
        if comp is None:
            raise ValueError(f"Competition {competition_id} not found")
        entries = self._repo.get_competition_entries(competition_id)
        return CompetitionDetail(competition=comp, entries=entries)

    def join_competition(self, competition_id: int, staff_key: int) -> bool:
        """Join a competition."""
        return self._repo.join_competition(competition_id, staff_key)

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------

    def get_feed(self, limit: int = 30) -> list[FeedItem]:
        """Return recent activity feed."""
        return self._repo.get_feed(limit)
