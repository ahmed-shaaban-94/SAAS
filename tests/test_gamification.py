"""Tests for gamification module — models, xp_engine, badge_rules, service."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from pydantic import ValidationError

from datapulse.gamification.badge_rules import StaffMetrics, evaluate_badges
from datapulse.gamification.models import (
    BadgeResponse,
    CompetitionCreate,
    CompetitionResponse,
    FeedItem,
    GamificationProfile,
    LeaderboardEntry,
    StaffBadgeResponse,
    StaffLevelResponse,
    StreakResponse,
)
from datapulse.gamification.repository import GamificationRepository
from datapulse.gamification.service import GamificationService
from datapulse.gamification.xp_engine import (
    get_xp_for_source,
    level_from_xp,
    streak_multiplier,
    tier_from_level,
    xp_for_level,
    xp_to_next,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> GamificationRepository:
    return GamificationRepository(mock_session)


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(GamificationRepository, instance=True)


@pytest.fixture()
def service(mock_repo: MagicMock) -> GamificationService:
    return GamificationService(mock_repo)


NOW = datetime(2025, 6, 15, 12, 0, 0)
TODAY = date(2025, 6, 15)


# ══════════════════════════════════════════════════════════════════════
# XP Engine tests
# ══════════════════════════════════════════════════════════════════════


class TestXPEngine:
    """Tests for xp_engine calculations."""

    def test_xp_for_level_1(self):
        assert xp_for_level(1) == 0

    def test_xp_for_level_2(self):
        assert xp_for_level(2) == int(1000 * (2**1.5))

    def test_xp_for_level_10(self):
        assert xp_for_level(10) == int(1000 * (10**1.5))

    def test_xp_for_level_0(self):
        assert xp_for_level(0) == 0

    def test_level_from_xp_zero(self):
        assert level_from_xp(0) == 1

    def test_level_from_xp_exact_boundary(self):
        xp_needed = xp_for_level(2)
        assert level_from_xp(xp_needed) == 2

    def test_level_from_xp_just_below(self):
        xp_needed = xp_for_level(2)
        assert level_from_xp(xp_needed - 1) == 1

    def test_level_from_xp_high(self):
        level = level_from_xp(1_000_000)
        assert level > 1

    def test_xp_to_next_level_1(self):
        remaining = xp_to_next(0)
        assert remaining == xp_for_level(2)

    def test_xp_to_next_at_cap(self):
        huge_xp = xp_for_level(100) + 999999
        assert xp_to_next(huge_xp) == 0

    def test_tier_from_level_bronze(self):
        assert tier_from_level(1) == "bronze"
        assert tier_from_level(14) == "bronze"

    def test_tier_from_level_silver(self):
        assert tier_from_level(15) == "silver"
        assert tier_from_level(29) == "silver"

    def test_tier_from_level_gold(self):
        assert tier_from_level(30) == "gold"
        assert tier_from_level(49) == "gold"

    def test_tier_from_level_platinum(self):
        assert tier_from_level(50) == "platinum"
        assert tier_from_level(79) == "platinum"

    def test_tier_from_level_diamond(self):
        assert tier_from_level(80) == "diamond"
        assert tier_from_level(100) == "diamond"

    def test_get_xp_for_source_known(self):
        assert get_xp_for_source("sale") == 10
        assert get_xp_for_source("daily_target_hit") == 100
        assert get_xp_for_source("competition_win") == 2000

    def test_get_xp_for_source_unknown(self):
        assert get_xp_for_source("unknown_source") == 0

    def test_streak_multiplier_short(self):
        assert streak_multiplier(3) == 1.0

    def test_streak_multiplier_7(self):
        assert streak_multiplier(7) == 1.25

    def test_streak_multiplier_14(self):
        assert streak_multiplier(14) == 1.5

    def test_streak_multiplier_30(self):
        assert streak_multiplier(30) == 2.0
        assert streak_multiplier(90) == 2.0


# ══════════════════════════════════════════════════════════════════════
# Badge Rules tests
# ══════════════════════════════════════════════════════════════════════


class TestBadgeRules:
    """Tests for badge evaluation logic."""

    def test_first_sale_qualifies(self):
        metrics = StaffMetrics(staff_key=1, total_sales_count=1)
        result = evaluate_badges(metrics, set())
        assert "first_sale" in result

    def test_first_sale_already_earned(self):
        metrics = StaffMetrics(staff_key=1, total_sales_count=1)
        result = evaluate_badges(metrics, {"first_sale"})
        assert "first_sale" not in result

    def test_century_club(self):
        metrics = StaffMetrics(staff_key=1, monthly_txn_count=100)
        result = evaluate_badges(metrics, set())
        assert "century_club" in result

    def test_century_club_not_enough(self):
        metrics = StaffMetrics(staff_key=1, monthly_txn_count=99)
        result = evaluate_badges(metrics, set())
        assert "century_club" not in result

    def test_million_maker(self):
        metrics = StaffMetrics(staff_key=1, monthly_revenue=Decimal("1000000"))
        result = evaluate_badges(metrics, set())
        assert "million_maker" in result
        assert "quarter_million" in result

    def test_streak_badges(self):
        metrics = StaffMetrics(staff_key=1, current_streak_days=30)
        result = evaluate_badges(metrics, set())
        assert "streak_7" in result
        assert "streak_30" in result
        assert "streak_90" not in result

    def test_customer_magnet(self):
        metrics = StaffMetrics(staff_key=1, monthly_customers=50)
        result = evaluate_badges(metrics, set())
        assert "customer_magnet" in result

    def test_comeback_king(self):
        metrics = StaffMetrics(staff_key=1, mom_growth_pct=Decimal("50"))
        result = evaluate_badges(metrics, set())
        assert "comeback_king" in result

    def test_perfect_quarter(self):
        metrics = StaffMetrics(staff_key=1, consecutive_100pct_months=3)
        result = evaluate_badges(metrics, set())
        assert "perfect_quarter" in result

    def test_top_performer(self):
        metrics = StaffMetrics(staff_key=1, rank_in_competition=1)
        result = evaluate_badges(metrics, set())
        assert "top_performer" in result

    def test_zero_returns(self):
        metrics = StaffMetrics(staff_key=1, monthly_returns=0, monthly_txn_count=10)
        result = evaluate_badges(metrics, set())
        assert "zero_returns" in result

    def test_zero_returns_no_sales(self):
        metrics = StaffMetrics(staff_key=1, monthly_returns=0, monthly_txn_count=0)
        result = evaluate_badges(metrics, set())
        assert "zero_returns" not in result

    def test_no_badges_earned(self):
        metrics = StaffMetrics(staff_key=1)
        result = evaluate_badges(metrics, set())
        assert result == []


# ══════════════════════════════════════════════════════════════════════
# Model tests
# ══════════════════════════════════════════════════════════════════════


class TestModels:
    """Tests for gamification Pydantic models."""

    def test_badge_response(self):
        badge = BadgeResponse(
            badge_id=1,
            badge_key="first_sale",
            title_en="First Sale",
            icon="sparkles",
            tier="bronze",
            category="milestone",
        )
        assert badge.badge_key == "first_sale"
        assert badge.tier == "bronze"

    def test_staff_badge_response(self):
        sb = StaffBadgeResponse(
            badge_id=1,
            badge_key="first_sale",
            title_en="First Sale",
            icon="sparkles",
            tier="bronze",
            category="milestone",
            earned_at=NOW,
        )
        assert sb.earned_at == NOW

    def test_streak_response_defaults(self):
        s = StreakResponse(streak_type="daily_target")
        assert s.current_count == 0
        assert s.best_count == 0
        assert s.last_date is None

    def test_gamification_profile(self):
        profile = GamificationProfile(
            staff_key=1,
            level=5,
            total_xp=3000,
            current_tier="bronze",
            xp_to_next_level=500,
        )
        assert profile.level == 5
        assert profile.badge_count == 0

    def test_competition_create(self):
        comp = CompetitionCreate(
            title="March Madness",
            metric="revenue",
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
        )
        assert comp.title == "March Madness"

    def test_leaderboard_entry(self):
        entry = LeaderboardEntry(
            rank=1,
            staff_key=42,
            staff_name="Ahmed",
            level=10,
            total_xp=10000,
            current_tier="silver",
            badge_count=5,
        )
        assert entry.rank == 1
        assert entry.staff_name == "Ahmed"

    def test_feed_item(self):
        item = FeedItem(
            id=1,
            staff_key=1,
            event_type="badge_earned",
            title="Earned badge",
            created_at=NOW,
        )
        assert item.event_type == "badge_earned"

    def test_frozen_models_immutable(self):
        badge = BadgeResponse(badge_id=1, badge_key="x", title_en="X")
        with pytest.raises((TypeError, AttributeError, ValidationError)):
            badge.badge_key = "y"

    def test_staff_level_response_defaults(self):
        sl = StaffLevelResponse(staff_key=1)
        assert sl.level == 1
        assert sl.total_xp == 0
        assert sl.current_tier == "bronze"


# ══════════════════════════════════════════════════════════════════════
# Service tests
# ══════════════════════════════════════════════════════════════════════


class TestGamificationService:
    """Tests for GamificationService business logic."""

    def test_get_profile_no_level(self, service, mock_repo):
        mock_repo.get_staff_level.return_value = None
        mock_repo.get_staff_badges.return_value = []
        mock_repo.get_streaks.return_value = []

        profile = service.get_profile(42)
        assert profile.staff_key == 42
        assert profile.level == 1
        assert profile.total_xp == 0

    def test_get_profile_with_level(self, service, mock_repo):
        mock_repo.get_staff_level.return_value = StaffLevelResponse(
            staff_key=42,
            level=5,
            total_xp=5000,
            current_tier="bronze",
        )
        mock_repo.get_staff_badges.return_value = [
            StaffBadgeResponse(
                badge_id=1,
                badge_key="first_sale",
                title_en="First Sale",
                icon="sparkles",
                tier="bronze",
                category="milestone",
                earned_at=NOW,
            )
        ]
        mock_repo.get_streaks.return_value = []

        profile = service.get_profile(42)
        assert profile.level == 5
        assert profile.badge_count == 1

    def test_list_badges(self, service, mock_repo):
        mock_repo.list_badges.return_value = [
            BadgeResponse(badge_id=1, badge_key="first_sale", title_en="First Sale"),
        ]
        badges = service.list_badges()
        assert len(badges) == 1

    def test_evaluate_and_award_new_badge(self, service, mock_repo):
        mock_repo.get_earned_badge_keys.return_value = set()
        mock_repo.award_badge.return_value = True
        mock_repo.get_staff_level.return_value = StaffLevelResponse(
            staff_key=1,
            level=1,
            total_xp=0,
        )
        mock_repo.get_total_xp.return_value = 150

        metrics = StaffMetrics(staff_key=1, total_sales_count=1)
        newly = service.evaluate_and_award(metrics)
        assert "first_sale" in newly
        mock_repo.award_badge.assert_called()
        mock_repo.add_feed_event.assert_called()

    def test_evaluate_and_award_already_earned(self, service, mock_repo):
        mock_repo.get_earned_badge_keys.return_value = {"first_sale"}

        metrics = StaffMetrics(staff_key=1, total_sales_count=1)
        newly = service.evaluate_and_award(metrics)
        assert "first_sale" not in newly

    def test_grant_xp(self, service, mock_repo):
        mock_repo.get_staff_level.return_value = StaffLevelResponse(
            staff_key=1,
            level=1,
            total_xp=0,
        )
        mock_repo.get_total_xp.return_value = 10

        result = service.grant_xp(1, "sale")
        mock_repo.add_xp.assert_called_once_with(1, 10, "sale", None)
        mock_repo.upsert_level.assert_called_once()
        assert result.total_xp == 10

    def test_grant_xp_unknown_source(self, service, mock_repo):
        mock_repo.get_staff_level.return_value = StaffLevelResponse(
            staff_key=1,
            level=1,
            total_xp=100,
        )

        service.grant_xp(1, "unknown_source")
        mock_repo.add_xp.assert_not_called()

    def test_grant_xp_level_up(self, service, mock_repo):
        mock_repo.get_staff_level.return_value = StaffLevelResponse(
            staff_key=1,
            level=1,
            total_xp=2800,
        )
        mock_repo.get_total_xp.return_value = 2900

        result = service.grant_xp(1, "daily_target_hit")
        assert result.level >= 2
        mock_repo.add_feed_event.assert_called()

    def test_record_streak(self, service, mock_repo):
        mock_repo.update_streak.return_value = StreakResponse(
            streak_type="daily_target",
            current_count=3,
            best_count=3,
            last_date=TODAY,
        )
        mock_repo.get_staff_level.return_value = StaffLevelResponse(staff_key=1)
        mock_repo.get_total_xp.return_value = 0

        result = service.record_streak(1, "daily_target", TODAY)
        assert result.current_count == 3
        mock_repo.update_streak.assert_called_once()

    def test_record_streak_milestone_7(self, service, mock_repo):
        mock_repo.update_streak.return_value = StreakResponse(
            streak_type="daily_target",
            current_count=7,
            best_count=7,
            last_date=TODAY,
        )
        mock_repo.get_staff_level.return_value = StaffLevelResponse(staff_key=1)
        mock_repo.get_total_xp.return_value = 200

        service.record_streak(1, "daily_target", TODAY)
        mock_repo.add_xp.assert_called()
        mock_repo.add_feed_event.assert_called()

    def test_list_competitions(self, service, mock_repo):
        mock_repo.list_competitions.return_value = [
            CompetitionResponse(
                competition_id=1,
                title="Q1 Race",
                competition_type="individual",
                metric="revenue",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                status="active",
                created_at=NOW,
            )
        ]
        comps = service.list_competitions("active")
        assert len(comps) == 1
        mock_repo.list_competitions.assert_called_with("active")

    def test_get_competition_detail(self, service, mock_repo):
        mock_repo.list_competitions.return_value = [
            CompetitionResponse(
                competition_id=1,
                title="Q1 Race",
                competition_type="individual",
                metric="revenue",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                status="active",
                created_at=NOW,
            )
        ]
        mock_repo.get_competition_entries.return_value = []
        detail = service.get_competition_detail(1)
        assert detail.competition.title == "Q1 Race"
        assert detail.entries == []

    def test_get_competition_detail_not_found(self, service, mock_repo):
        mock_repo.list_competitions.return_value = []
        with pytest.raises(ValueError, match="not found"):
            service.get_competition_detail(999)

    def test_get_feed(self, service, mock_repo):
        mock_repo.get_feed.return_value = [
            FeedItem(
                id=1,
                staff_key=1,
                event_type="badge_earned",
                title="Earned badge",
                created_at=NOW,
            )
        ]
        feed = service.get_feed(10)
        assert len(feed) == 1
        mock_repo.get_feed.assert_called_with(10)

    def test_join_competition(self, service, mock_repo):
        mock_repo.join_competition.return_value = True
        result = service.join_competition(1, 42)
        assert result is True

    def test_get_leaderboard(self, service, mock_repo):
        mock_repo.get_leaderboard.return_value = [
            LeaderboardEntry(
                rank=1,
                staff_key=42,
                staff_name="Ahmed",
                level=10,
                total_xp=10000,
                current_tier="silver",
                badge_count=5,
            )
        ]
        lb = service.get_leaderboard(10)
        assert len(lb) == 1
        assert lb[0].rank == 1
