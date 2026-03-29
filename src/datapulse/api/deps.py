"""FastAPI dependency injection for database sessions and services."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

import structlog
from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from datapulse.analytics.repository import AnalyticsRepository
from datapulse.analytics.service import AnalyticsService
from datapulse.config import get_settings
from datapulse.pipeline.executor import PipelineExecutor
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.quality_service import QualityService
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService

logger = structlog.get_logger()

_engine = None
_session_factory = None


def get_engine():
    """Return the SQLAlchemy engine singleton (with connection pooling)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_pool_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        # Set tenant context for RLS — default tenant_id=1 for dev mode
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": "1"})
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
