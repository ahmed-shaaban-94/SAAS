"""FastAPI dependency injection for database sessions and services."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from datapulse.analytics.repository import AnalyticsRepository
from datapulse.analytics.service import AnalyticsService
from datapulse.config import get_settings

logger = structlog.get_logger()

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=_get_engine())
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_analytics_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    return AnalyticsService(repo)
