"""Repository for gamification — raw SQL via SQLAlchemy text().

All queries use parameterized placeholders to prevent SQL injection.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.gamification.models import (
    BadgeResponse,
    CompetitionCreate,
    CompetitionEntryResponse,
    CompetitionResponse,
    FeedItem,
    LeaderboardEntry,
    StaffBadgeResponse,
    StaffLevelResponse,
    StreakResponse,
    XPEvent,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class GamificationRepository:
    """Data-access layer for the gamification system."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Badges
    # ------------------------------------------------------------------

    def list_badges(self) -> list[BadgeResponse]:
        """Return all active badge definitions."""
        rows = (
            self._session.execute(
                text("""
                SELECT badge_id, badge_key, title_en, title_ar,
                       description_en, description_ar, icon, tier,
                       category, is_active
                FROM public.badges
                WHERE is_active = TRUE
                ORDER BY tier, category, badge_key
            """)
            )
            .mappings()
            .fetchall()
        )
        return [BadgeResponse(**r) for r in rows]

    def get_staff_badges(self, staff_key: int) -> list[StaffBadgeResponse]:
        """Return all badges earned by a given staff member."""
        rows = (
            self._session.execute(
                text("""
                SELECT b.badge_id, b.badge_key, b.title_en, b.title_ar,
                       b.icon, b.tier, b.category,
                       sb.earned_at, sb.context
                FROM public.staff_badges sb
                JOIN public.badges b ON b.badge_id = sb.badge_id
                WHERE sb.staff_key = :staff_key
                ORDER BY sb.earned_at DESC
            """),
                {"staff_key": staff_key},
            )
            .mappings()
            .fetchall()
        )
        return [StaffBadgeResponse(**r) for r in rows]

    def get_earned_badge_keys(self, staff_key: int) -> set[str]:
        """Return badge_keys already earned by a staff member."""
        rows = self._session.execute(
            text("""
                SELECT b.badge_key
                FROM public.staff_badges sb
                JOIN public.badges b ON b.badge_id = sb.badge_id
                WHERE sb.staff_key = :staff_key
            """),
            {"staff_key": staff_key},
        ).fetchall()
        return {r[0] for r in rows}

    def award_badge(self, staff_key: int, badge_key: str, context: dict | None = None) -> bool:
        """Award a badge to a staff member. Returns True if newly awarded."""
        log.info("award_badge", staff_key=staff_key, badge_key=badge_key)
        result = self._session.execute(
            text("""
                INSERT INTO public.staff_badges (staff_key, badge_id, context)
                SELECT :staff_key, badge_id, :context::jsonb
                FROM public.badges
                WHERE badge_key = :badge_key
                ON CONFLICT (tenant_id, staff_key, badge_id) DO NOTHING
                RETURNING id
            """),
            {
                "staff_key": staff_key,
                "badge_key": badge_key,
                "context": "{}" if context is None else str(context).replace("'", '"'),
            },
        ).fetchone()
        return result is not None

    # ------------------------------------------------------------------
    # Streaks
    # ------------------------------------------------------------------

    def get_streaks(self, staff_key: int) -> list[StreakResponse]:
        """Return all streak records for a staff member."""
        rows = (
            self._session.execute(
                text("""
                SELECT streak_type, current_count, best_count, last_date
                FROM public.streaks
                WHERE staff_key = :staff_key
                ORDER BY streak_type
            """),
                {"staff_key": staff_key},
            )
            .mappings()
            .fetchall()
        )
        return [StreakResponse(**r) for r in rows]

    def update_streak(
        self,
        staff_key: int,
        streak_type: str,
        today: date,
    ) -> StreakResponse:
        """Increment or reset a streak based on the date."""
        log.info("update_streak", staff_key=staff_key, streak_type=streak_type)
        row = (
            self._session.execute(
                text("""
                INSERT INTO public.streaks
                    (staff_key, streak_type, current_count, best_count, last_date)
                VALUES (:staff_key, :streak_type, 1, 1, :today)
                ON CONFLICT (tenant_id, staff_key, streak_type) DO UPDATE SET
                    current_count = CASE
                        WHEN streaks.last_date = :today - INTERVAL '1 day'
                        THEN streaks.current_count + 1
                        WHEN streaks.last_date = :today THEN streaks.current_count
                        ELSE 1
                    END,
                    best_count = GREATEST(
                        streaks.best_count,
                        CASE
                            WHEN streaks.last_date = :today - INTERVAL '1 day'
                            THEN streaks.current_count + 1
                            ELSE 1
                        END
                    ),
                    last_date = :today,
                    updated_at = NOW()
                RETURNING streak_type, current_count, best_count, last_date
            """),
                {"staff_key": staff_key, "streak_type": streak_type, "today": today},
            )
            .mappings()
            .fetchone()
        )
        assert row is not None, "INSERT ... RETURNING must return a row"
        return StreakResponse(**dict(row))

    # ------------------------------------------------------------------
    # XP & Levels
    # ------------------------------------------------------------------

    def add_xp(
        self,
        staff_key: int,
        xp_amount: int,
        source: str,
        source_ref: str | None = None,
    ) -> None:
        """Record an XP event in the ledger."""
        self._session.execute(
            text("""
                INSERT INTO public.xp_ledger (staff_key, xp_amount, source, source_ref)
                VALUES (:staff_key, :xp_amount, :source, :source_ref)
            """),
            {
                "staff_key": staff_key,
                "xp_amount": xp_amount,
                "source": source,
                "source_ref": source_ref,
            },
        )

    def get_total_xp(self, staff_key: int) -> int:
        """Return total XP for a staff member."""
        row = self._session.execute(
            text(
                "SELECT COALESCE(SUM(xp_amount), 0) AS total"
                " FROM public.xp_ledger WHERE staff_key = :sk"
            ),
            {"sk": staff_key},
        ).fetchone()
        return int(row[0]) if row else 0

    def upsert_level(self, staff_key: int, level: int, total_xp: int, tier: str) -> None:
        """Update or insert the staff level record."""
        self._session.execute(
            text("""
                INSERT INTO public.staff_levels (staff_key, level, total_xp, current_tier)
                VALUES (:sk, :level, :xp, :tier)
                ON CONFLICT (tenant_id, staff_key) DO UPDATE SET
                    level = :level,
                    total_xp = :xp,
                    current_tier = :tier,
                    updated_at = NOW()
            """),
            {"sk": staff_key, "level": level, "xp": total_xp, "tier": tier},
        )

    def get_staff_level(self, staff_key: int) -> StaffLevelResponse | None:
        """Get level info for one staff member."""
        row = (
            self._session.execute(
                text("""
                SELECT staff_key, level, total_xp, current_tier
                FROM public.staff_levels
                WHERE staff_key = :sk
            """),
                {"sk": staff_key},
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            return None
        from datapulse.gamification.xp_engine import xp_to_next

        return StaffLevelResponse(
            **dict(row),
            xp_to_next_level=xp_to_next(row["total_xp"]),  # type: ignore[arg-type]
        )

    def get_xp_history(self, staff_key: int, limit: int = 50) -> list[XPEvent]:
        """Return recent XP events for a staff member."""
        rows = (
            self._session.execute(
                text("""
                SELECT id, xp_amount, source, source_ref, earned_at
                FROM public.xp_ledger
                WHERE staff_key = :sk
                ORDER BY earned_at DESC
                LIMIT :lim
            """),
                {"sk": staff_key, "lim": limit},
            )
            .mappings()
            .fetchall()
        )
        return [XPEvent(**r) for r in rows]

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_leaderboard(self, limit: int = 20) -> list[LeaderboardEntry]:
        """Return top staff by XP with level and badge count."""
        rows = (
            self._session.execute(
                text("""
                SELECT
                    ROW_NUMBER() OVER (ORDER BY sl.total_xp DESC) AS rank,
                    sl.staff_key,
                    COALESCE(ds.staff_name, 'Staff #' || sl.staff_key) AS staff_name,
                    sl.level,
                    sl.total_xp,
                    sl.current_tier,
                    COALESCE(bc.cnt, 0) AS badge_count
                FROM public.staff_levels sl
                LEFT JOIN public_marts.dim_staff ds ON ds.staff_key = sl.staff_key
                LEFT JOIN (
                    SELECT staff_key, COUNT(*) AS cnt
                    FROM public.staff_badges
                    GROUP BY staff_key
                ) bc ON bc.staff_key = sl.staff_key
                ORDER BY sl.total_xp DESC
                LIMIT :lim
            """),
                {"lim": limit},
            )
            .mappings()
            .fetchall()
        )
        return [LeaderboardEntry(**r) for r in rows]

    # ------------------------------------------------------------------
    # Competitions
    # ------------------------------------------------------------------

    def create_competition(self, data: CompetitionCreate, created_by: str) -> CompetitionResponse:
        """Create a new competition."""
        log.info("create_competition", title=data.title, metric=data.metric)
        row = (
            self._session.execute(
                text("""
                INSERT INTO public.competitions
                    (title, description, competition_type, metric, start_date, end_date,
                     prize_description, created_by)
                VALUES
                    (:title, :desc, :ctype, :metric, :start, :end, :prize, :by)
                RETURNING competition_id, title, description, competition_type, metric,
                          start_date, end_date, status, prize_description, created_at
            """),
                {
                    "title": data.title,
                    "desc": data.description,
                    "ctype": data.competition_type,
                    "metric": data.metric,
                    "start": data.start_date,
                    "end": data.end_date,
                    "prize": data.prize_description,
                    "by": created_by,
                },
            )
            .mappings()
            .fetchone()
        )
        assert row is not None, "INSERT ... RETURNING must return a row"
        return CompetitionResponse(**dict(row))

    def list_competitions(self, status: str | None = None) -> list[CompetitionResponse]:
        """List competitions, optionally filtered by status."""
        if status:
            rows = (
                self._session.execute(
                    text("""
                    SELECT competition_id, title, description, competition_type, metric,
                           start_date, end_date, status, prize_description, created_at
                    FROM public.competitions
                    WHERE status = :status
                    ORDER BY start_date DESC
                """),
                    {"status": status},
                )
                .mappings()
                .fetchall()
            )
        else:
            rows = (
                self._session.execute(
                    text("""
                    SELECT competition_id, title, description, competition_type, metric,
                           start_date, end_date, status, prize_description, created_at
                    FROM public.competitions
                    ORDER BY start_date DESC
                """),
                )
                .mappings()
                .fetchall()
            )
        return [CompetitionResponse(**r) for r in rows]

    def get_competition_entries(self, competition_id: int) -> list[CompetitionEntryResponse]:
        """Return leaderboard entries for a competition."""
        rows = (
            self._session.execute(
                text("""
                SELECT
                    ce.staff_key,
                    COALESCE(ds.staff_name, 'Staff #' || ce.staff_key) AS staff_name,
                    ce.score,
                    ce.rank
                FROM public.competition_entries ce
                LEFT JOIN public_marts.dim_staff ds ON ds.staff_key = ce.staff_key
                WHERE ce.competition_id = :cid
                ORDER BY ce.score DESC
            """),
                {"cid": competition_id},
            )
            .mappings()
            .fetchall()
        )
        return [CompetitionEntryResponse(**r) for r in rows]

    def join_competition(self, competition_id: int, staff_key: int) -> bool:
        """Register a staff member in a competition. Returns True if newly joined."""
        result = self._session.execute(
            text("""
                INSERT INTO public.competition_entries (competition_id, staff_key, score)
                VALUES (:cid, :sk, 0)
                ON CONFLICT (tenant_id, competition_id, staff_key) DO NOTHING
                RETURNING id
            """),
            {"cid": competition_id, "sk": staff_key},
        ).fetchone()
        return result is not None

    # ------------------------------------------------------------------
    # Activity Feed
    # ------------------------------------------------------------------

    def add_feed_event(
        self,
        staff_key: int,
        event_type: str,
        title: str,
        description: str = "",
        metadata: dict | None = None,
    ) -> None:
        """Insert a gamification feed event."""
        import json

        self._session.execute(
            text("""
                INSERT INTO public.gamification_feed
                    (staff_key, event_type, title, description, metadata)
                VALUES (:sk, :etype, :title, :desc, :meta::jsonb)
            """),
            {
                "sk": staff_key,
                "etype": event_type,
                "title": title,
                "desc": description,
                "meta": json.dumps(metadata or {}),
            },
        )

    def get_feed(self, limit: int = 30) -> list[FeedItem]:
        """Return recent activity feed items."""
        rows = (
            self._session.execute(
                text("""
                SELECT
                    gf.id, gf.staff_key,
                    COALESCE(ds.staff_name, 'Staff #' || gf.staff_key) AS staff_name,
                    gf.event_type, gf.title, gf.description, gf.metadata, gf.created_at
                FROM public.gamification_feed gf
                LEFT JOIN public_marts.dim_staff ds ON ds.staff_key = gf.staff_key
                ORDER BY gf.created_at DESC
                LIMIT :lim
            """),
                {"lim": limit},
            )
            .mappings()
            .fetchall()
        )
        return [FeedItem(**r) for r in rows]
