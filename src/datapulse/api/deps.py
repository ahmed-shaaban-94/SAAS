"""FastAPI dependency injection for database sessions and services."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from datapulse.ai_light.service import AILightService
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.analytics.service import AnalyticsService
from datapulse.config import get_settings
from datapulse.pipeline.executor import PipelineExecutor
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.quality_service import QualityService
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService

logger = structlog.get_logger()


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Validate the X-API-Key header against the configured API key."""
    settings = get_settings()
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


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
        # Set RLS tenant context for row-level security
        session.execute(text("SET LOCAL app.tenant_id = '1'"))
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_analytics_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    return AnalyticsService(repo)


def get_pipeline_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PipelineService:
    repo = PipelineRepository(session)
    return PipelineService(repo)


def get_pipeline_executor() -> PipelineExecutor:
    settings = get_settings()
    return PipelineExecutor(settings=settings)


def get_quality_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> QualityService:
    repo = QualityRepository(session)
    settings = get_settings()
    return QualityService(repo, session, settings)


def get_ai_light_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AILightService:
    settings = get_settings()
    return AILightService(settings, session)
