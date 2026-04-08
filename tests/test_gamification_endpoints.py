"""Tests for gamification API endpoints."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.gamification.models import (
    BadgeResponse,
    CompetitionDetail,
    CompetitionResponse,
    FeedItem,
    GamificationProfile,
    LeaderboardEntry,
    StaffBadgeResponse,
    StreakResponse,
    XPEvent,
)
from datapulse.gamification.service import GamificationService

NOW = datetime(2025, 6, 15, 12, 0, 0)

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(GamificationService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()

    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()

    from datapulse.api.routes.gamification import get_gamification_service

    app.dependency_overrides[get_gamification_service] = lambda: mock_service

    return TestClient(app)


# ── Profile ─────────────────────────────────────────────────────────


class TestProfileEndpoint:
    def test_get_profile(self, client, mock_service):
        mock_service.get_profile.return_value = GamificationProfile(
            staff_key=42, level=5, total_xp=5000, current_tier="bronze",
            xp_to_next_level=1000,
        )
        resp = client.get("/api/v1/gamification/profile/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["staff_key"] == 42
        assert data["level"] == 5

    def test_get_profile_invalid_key(self, client):
        resp = client.get("/api/v1/gamification/profile/0")
        assert resp.status_code == 422


# ── Badges ──────────────────────────────────────────────────────────


class TestBadgeEndpoints:
    def test_list_badges(self, client, mock_service):
        mock_service.list_badges.return_value = [
            BadgeResponse(badge_id=1, badge_key="first_sale", title_en="First Sale"),
        ]
        resp = client.get("/api/v1/gamification/badges")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_staff_badges(self, client, mock_service):
        mock_service.get_staff_badges.return_value = [
            StaffBadgeResponse(
                badge_id=1, badge_key="first_sale", title_en="First Sale",
                icon="sparkles", tier="bronze", category="milestone",
                earned_at=NOW,
            ),
        ]
        resp = client.get("/api/v1/gamification/badges/42")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["badge_key"] == "first_sale"


# ── Streaks ─────────────────────────────────────────────────────────


class TestStreakEndpoints:
    def test_get_streaks(self, client, mock_service):
        mock_service.get_streaks.return_value = [
            StreakResponse(streak_type="daily_target", current_count=5, best_count=10),
        ]
        resp = client.get("/api/v1/gamification/streaks/42")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["current_count"] == 5


# ── XP History ──────────────────────────────────────────────────────


class TestXPEndpoints:
    def test_get_xp_history(self, client, mock_service):
        mock_service.get_xp_history.return_value = [
            XPEvent(id=1, xp_amount=10, source="sale", earned_at=NOW),
        ]
        resp = client.get("/api/v1/gamification/xp/42/history")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_xp_history_with_limit(self, client, mock_service):
        mock_service.get_xp_history.return_value = []
        resp = client.get("/api/v1/gamification/xp/42/history?limit=5")
        assert resp.status_code == 200
        mock_service.get_xp_history.assert_called_with(42, 5)


# ── Leaderboard ─────────────────────────────────────────────────────


class TestLeaderboardEndpoints:
    def test_get_leaderboard(self, client, mock_service):
        mock_service.get_leaderboard.return_value = [
            LeaderboardEntry(
                rank=1, staff_key=42, staff_name="Ahmed",
                level=10, total_xp=10000, current_tier="silver", badge_count=5,
            ),
        ]
        resp = client.get("/api/v1/gamification/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rank"] == 1

    def test_get_leaderboard_with_limit(self, client, mock_service):
        mock_service.get_leaderboard.return_value = []
        resp = client.get("/api/v1/gamification/leaderboard?limit=5")
        assert resp.status_code == 200
        mock_service.get_leaderboard.assert_called_with(5)


# ── Competitions ────────────────────────────────────────────────────


class TestCompetitionEndpoints:
    def test_list_competitions(self, client, mock_service):
        mock_service.list_competitions.return_value = [
            CompetitionResponse(
                competition_id=1, title="Q1 Race", competition_type="individual",
                metric="revenue", start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31), status="active", created_at=NOW,
            ),
        ]
        resp = client.get("/api/v1/gamification/competitions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_competition(self, client, mock_service):
        mock_service.create_competition.return_value = CompetitionResponse(
            competition_id=1, title="March Madness", competition_type="individual",
            metric="revenue", start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31), status="upcoming", created_at=NOW,
        )
        resp = client.post("/api/v1/gamification/competitions", json={
            "title": "March Madness",
            "metric": "revenue",
            "start_date": "2025-03-01",
            "end_date": "2025-03-31",
        })
        assert resp.status_code == 201
        assert resp.json()["title"] == "March Madness"

    def test_get_competition_detail(self, client, mock_service):
        mock_service.get_competition_detail.return_value = CompetitionDetail(
            competition=CompetitionResponse(
                competition_id=1, title="Q1", competition_type="individual",
                metric="revenue", start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31), status="active", created_at=NOW,
            ),
            entries=[],
        )
        resp = client.get("/api/v1/gamification/competitions/1")
        assert resp.status_code == 200
        assert resp.json()["competition"]["title"] == "Q1"

    def test_get_competition_not_found(self, client, mock_service):
        mock_service.get_competition_detail.side_effect = ValueError("not found")
        resp = client.get("/api/v1/gamification/competitions/999")
        assert resp.status_code == 404

    def test_join_competition(self, client, mock_service):
        mock_service.join_competition.return_value = True
        resp = client.post("/api/v1/gamification/competitions/1/join?staff_key=42")
        assert resp.status_code == 204


# ── Feed ────────────────────────────────────────────────────────────


class TestFeedEndpoints:
    def test_get_feed(self, client, mock_service):
        mock_service.get_feed.return_value = [
            FeedItem(
                id=1, staff_key=1, event_type="badge_earned",
                title="Earned badge", created_at=NOW,
            ),
        ]
        resp = client.get("/api/v1/gamification/feed")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_feed_with_limit(self, client, mock_service):
        mock_service.get_feed.return_value = []
        resp = client.get("/api/v1/gamification/feed?limit=10")
        assert resp.status_code == 200
        mock_service.get_feed.assert_called_with(10)
