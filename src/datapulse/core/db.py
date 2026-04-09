"""Database engine and session factory singletons.

Provides thread-safe lazy initialization of the SQLAlchemy engine
and session factory, importable from anywhere without pulling in
FastAPI-specific dependencies.
"""

from __future__ import annotations

import os
import threading

import structlog
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from datapulse.core.config import get_settings

logger = structlog.get_logger()


def _validate_database_url(url: str) -> None:
    """Raise RuntimeError in production if DB connection does not use SSL."""
    env = os.getenv("SENTRY_ENVIRONMENT", "development")
    if env not in ("development", "test") and "sslmode=" not in url:
        raise RuntimeError(
            "DATABASE_URL must include sslmode= in non-development environments. "
            "Add ?sslmode=require (or sslmode=verify-full) to DATABASE_URL."
        )


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_init_lock = threading.Lock()


def get_engine() -> Engine:
    """Return the SQLAlchemy engine singleton (with connection pooling).

    Thread-safe: uses a lock to prevent duplicate engine creation
    when multiple requests arrive concurrently at startup.
    """
    global _engine
    if _engine is None:
        with _init_lock:
            if _engine is None:
                settings = get_settings()
                _validate_database_url(settings.database_url)
                _engine = create_engine(
                    settings.database_url,
                    pool_pre_ping=True,
                    pool_size=settings.db_pool_size,
                    max_overflow=settings.db_pool_max_overflow,
                    pool_timeout=settings.db_pool_timeout,
                    pool_recycle=settings.db_pool_recycle,
                )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the SQLAlchemy session factory singleton."""
    global _session_factory
    if _session_factory is None:
        with _init_lock:
            if _session_factory is None:
                _session_factory = sessionmaker(bind=get_engine())
    return _session_factory
