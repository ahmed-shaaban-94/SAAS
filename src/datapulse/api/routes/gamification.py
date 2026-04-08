"""Gamification API endpoints.

Provides badges, XP, streaks, competitions, leaderboard, and activity feed
under ``/gamification/``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.gamification.models import (
    BadgeResponse,
    CompetitionCreate,
    CompetitionDetail,
    CompetitionResponse,
    FeedItem,
    GamificationProfile,
    LeaderboardEntry,
    StaffBadgeResponse,
    StreakResponse,
    XPEvent,
)
from datapulse.gamification.repository import GamificationRepository
from datapulse.gamification.service import GamificationService

router = APIRouter(
    prefix="/gamification",
    tags=["gamification"],
    dependencies=[Depends(get_current_user)],
)


# ------------------------------------------------------------------
# Dependency injection
# ------------------------------------------------------------------


def get_gamification_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> GamificationService:
    repo = GamificationRepository(session)
    return GamificationService(repo)


ServiceDep = Annotated[GamificationService, Depends(get_gamification_service)]


def _set_cache(response: Response, max_age: int) -> None:
    response.headers["Cache-Control"] = f"max-age={max_age}, private"


# ------------------------------------------------------------------
# Profile
# ------------------------------------------------------------------


@router.get("/profile/{staff_key}", response_model=GamificationProfile)
@limiter.limit("60/minute")
def get_profile(
    request: Request,
    response: Response,
    staff_key: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> GamificationProfile:
    """Get full gamification profile for a staff member."""
    _set_cache(response, 60)
    return service.get_profile(staff_key)


# ------------------------------------------------------------------
# Badges
# ------------------------------------------------------------------


@router.get("/badges", response_model=list[BadgeResponse])
@limiter.limit("60/minute")
def list_badges(
    request: Request,
    response: Response,
    service: ServiceDep,
) -> list[BadgeResponse]:
    """List all available badges."""
    _set_cache(response, 300)
    return service.list_badges()


@router.get("/badges/{staff_key}", response_model=list[StaffBadgeResponse])
@limiter.limit("60/minute")
def get_staff_badges(
    request: Request,
    response: Response,
    staff_key: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> list[StaffBadgeResponse]:
    """Get badges earned by a staff member."""
    _set_cache(response, 60)
    return service.get_staff_badges(staff_key)


# ------------------------------------------------------------------
# Streaks
# ------------------------------------------------------------------


@router.get("/streaks/{staff_key}", response_model=list[StreakResponse])
@limiter.limit("60/minute")
def get_streaks(
    request: Request,
    response: Response,
    staff_key: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> list[StreakResponse]:
    """Get current streaks for a staff member."""
    _set_cache(response, 60)
    return service.get_streaks(staff_key)


# ------------------------------------------------------------------
# XP & Levels
# ------------------------------------------------------------------


@router.get("/xp/{staff_key}/history", response_model=list[XPEvent])
@limiter.limit("60/minute")
def get_xp_history(
    request: Request,
    response: Response,
    staff_key: int = Path(..., gt=0),
    limit: int = Query(50, ge=1, le=200),
    *,
    service: ServiceDep,
) -> list[XPEvent]:
    """Get XP history for a staff member."""
    _set_cache(response, 60)
    return service.get_xp_history(staff_key, limit)


# ------------------------------------------------------------------
# Leaderboard
# ------------------------------------------------------------------


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
@limiter.limit("60/minute")
def get_leaderboard(
    request: Request,
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    *,
    service: ServiceDep,
) -> list[LeaderboardEntry]:
    """Get XP leaderboard."""
    _set_cache(response, 120)
    return service.get_leaderboard(limit)


# ------------------------------------------------------------------
# Competitions
# ------------------------------------------------------------------


@router.get("/competitions", response_model=list[CompetitionResponse])
@limiter.limit("60/minute")
def list_competitions(
    request: Request,
    response: Response,
    status: str | None = Query(None),
    *,
    service: ServiceDep,
) -> list[CompetitionResponse]:
    """List competitions, optionally filtered by status."""
    _set_cache(response, 120)
    return service.list_competitions(status)


@router.post("/competitions", response_model=CompetitionResponse, status_code=201)
@limiter.limit("5/minute")
def create_competition(
    request: Request,
    data: CompetitionCreate,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> CompetitionResponse:
    """Create a new competition (admin only)."""
    return service.create_competition(data, created_by=user.get("sub", ""))


@router.get("/competitions/{competition_id}", response_model=CompetitionDetail)
@limiter.limit("60/minute")
def get_competition_detail(
    request: Request,
    response: Response,
    competition_id: int = Path(..., gt=0),
    *,
    service: ServiceDep,
) -> CompetitionDetail:
    """Get competition details with leaderboard."""
    _set_cache(response, 60)
    try:
        return service.get_competition_detail(competition_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/competitions/{competition_id}/join", status_code=204)
@limiter.limit("5/minute")
def join_competition(
    request: Request,
    competition_id: int = Path(..., gt=0),
    staff_key: int = Query(..., gt=0),
    *,
    service: ServiceDep,
) -> None:
    """Join a competition."""
    service.join_competition(competition_id, staff_key)


# ------------------------------------------------------------------
# Activity Feed
# ------------------------------------------------------------------


@router.get("/feed", response_model=list[FeedItem])
@limiter.limit("60/minute")
def get_feed(
    request: Request,
    response: Response,
    limit: int = Query(30, ge=1, le=100),
    *,
    service: ServiceDep,
) -> list[FeedItem]:
    """Get recent activity feed."""
    _set_cache(response, 30)
    return service.get_feed(limit)
