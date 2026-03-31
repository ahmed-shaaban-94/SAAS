"""FastAPI dependency injection for database sessions and services."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated, Any

import structlog
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.ai_light.service import AILightService
from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.comparison_repository import ComparisonRepository
from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.hierarchy_repository import HierarchyRepository
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.analytics.service import AnalyticsService
from datapulse.api.auth import get_current_user, require_api_key
from datapulse.config import get_settings
from datapulse.core.db import get_engine, get_session_factory  # noqa: F401 (get_engine re-exported for health.py)
from datapulse.pipeline.executor import PipelineExecutor
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.quality_service import QualityService
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService

logger = structlog.get_logger()


def get_db_session() -> Generator[Session, None, None]:
    """Create a DB session with tenant_id='1' (legacy, for non-authenticated use)."""
    session = get_session_factory()()
    try:
        # Execute inside the auto-begun transaction so SET LOCAL persists
        # for the entire request lifetime
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": "1"})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_tenant_session(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> Generator[Session, None, None]:
    """Create a DB session scoped to the authenticated user's tenant.

    Extracts tenant_id from the JWT claims and sets it via SET LOCAL
    so that PostgreSQL RLS policies filter data automatically.
    """
    tenant_id = user.get("tenant_id", "1")
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Type aliases for FastAPI dependency injection
SessionDep = Annotated[Session, Depends(get_tenant_session)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def get_analytics_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    detail_repo = DetailRepository(session)
    breakdown_repo = BreakdownRepository(session)
    comparison_repo = ComparisonRepository(session)
    hierarchy_repo = HierarchyRepository(session)
    return AnalyticsService(
        repo, detail_repo, breakdown_repo, comparison_repo, hierarchy_repo
    )


def get_pipeline_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> PipelineService:
    repo = PipelineRepository(session)
    return PipelineService(repo)


def get_pipeline_executor() -> PipelineExecutor:
    settings = get_settings()
    return PipelineExecutor(settings=settings)


def get_quality_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> QualityService:
    repo = QualityRepository(session)
    settings = get_settings()
    return QualityService(repo, session, settings)


def get_ai_light_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AILightService:
    """Factory for AI-Light service with analytics repo + OpenRouter client."""
    settings = get_settings()
    return AILightService(settings=settings, session=session)


# Alias for backwards compatibility — analytics.py and ai_light.py import this name
verify_api_key = require_api_key
