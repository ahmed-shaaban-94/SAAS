"""FastAPI dependency injection for database sessions and services."""

from __future__ import annotations

import hmac
from collections.abc import Generator
from contextvars import ContextVar
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, Request
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

# ContextVar to pass tenant_id from the dependency chain into get_db_session
_current_tenant_id: ContextVar[str] = ContextVar("_current_tenant_id", default="1")


async def get_tenant_id(x_tenant_id: str = Header(default="1")) -> str:
    """Extract tenant ID from X-Tenant-ID header (defaults to '1')."""
    _current_tenant_id.set(x_tenant_id)
    return x_tenant_id


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Validate the X-API-Key header against the configured API key."""
    settings = get_settings()
    if not settings.api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


_engine = None
_session_factory = None
_init_lock = __import__("threading").Lock()


def _get_engine():
    global _engine
    if _engine is None:
        with _init_lock:
            if _engine is None:
                settings = get_settings()
                _engine = create_engine(
                    settings.database_url,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        with _init_lock:
            if _session_factory is None:
                _session_factory = sessionmaker(bind=_get_engine())
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        # Set RLS tenant context for row-level security
        tenant_id = _current_tenant_id.get("1")
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_analytics_service(
    session: Annotated[Session, Depends(get_db_session)],
    _tenant_id: Annotated[str, Depends(get_tenant_id)] = "1",
) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    return AnalyticsService(repo)


def get_pipeline_service(
    session: Annotated[Session, Depends(get_db_session)],
    _tenant_id: Annotated[str, Depends(get_tenant_id)] = "1",
) -> PipelineService:
    repo = PipelineRepository(session)
    return PipelineService(repo)


def get_pipeline_executor() -> PipelineExecutor:
    settings = get_settings()
    return PipelineExecutor(settings=settings)


def get_quality_service(
    session: Annotated[Session, Depends(get_db_session)],
    _tenant_id: Annotated[str, Depends(get_tenant_id)] = "1",
) -> QualityService:
    repo = QualityRepository(session)
    settings = get_settings()
    return QualityService(repo, session, settings)


def get_ai_light_service(
    session: Annotated[Session, Depends(get_db_session)],
    _tenant_id: Annotated[str, Depends(get_tenant_id)] = "1",
) -> AILightService:
    settings = get_settings()
    return AILightService(settings, session)
