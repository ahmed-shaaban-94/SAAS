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
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
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
_readonly_engine: Engine | None = None
_readonly_session_factory: sessionmaker[Session] | None = None
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
_init_lock = threading.Lock()


def _to_async_url(url: str) -> str:
    """Rewrite a sync DB URL to its async driver equivalent."""
    if url.startswith("postgresql+asyncpg://") or url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


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
                    # Use PostgreSQL's multi-row INSERT … VALUES for bulk
                    # inserts (SQLAlchemy 2.0+ feature).  Sends up to 1 000
                    # rows per statement instead of one statement per row,
                    # reducing round-trips during bronze ingestion.
                    use_insertmanyvalues=True,
                    insertmanyvalues_page_size=1000,
                    # TCP-level connect timeout prevents indefinite hangs
                    # during startup (e.g. scheduler leader election) if
                    # PostgreSQL is temporarily unreachable after container
                    # recreation.
                    connect_args={"connect_timeout": 10},
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


def get_readonly_engine() -> Engine:
    """Return the read-replica engine singleton, or the primary if no replica is configured.

    When ``database_replica_url`` is set, heavy analytics queries route here
    instead of the primary. Falls back to the primary engine silently if the
    replica URL is unset — callers treat it as "best-effort read routing"
    rather than a hard dependency (#608).
    """
    global _readonly_engine
    if _readonly_engine is None:
        with _init_lock:
            if _readonly_engine is None:
                settings = get_settings()
                replica_url = settings.database_replica_url
                if not replica_url:
                    _readonly_engine = get_engine()
                else:
                    _validate_database_url(replica_url)
                    _readonly_engine = create_engine(
                        replica_url,
                        pool_pre_ping=True,
                        pool_size=settings.db_pool_size,
                        max_overflow=settings.db_pool_max_overflow,
                        pool_timeout=settings.db_pool_timeout,
                        pool_recycle=settings.db_pool_recycle,
                        connect_args={"connect_timeout": 10},
                    )
                    logger.info("readonly_engine_initialized", using_replica=True)
    return _readonly_engine


def get_readonly_session_factory() -> sessionmaker[Session]:
    """Return the read-replica session factory singleton."""
    global _readonly_session_factory
    if _readonly_session_factory is None:
        # Resolve the engine BEFORE acquiring _init_lock — get_readonly_engine
        # also takes _init_lock, and threading.Lock is not re-entrant.
        engine = get_readonly_engine()
        with _init_lock:
            if _readonly_session_factory is None:
                _readonly_session_factory = sessionmaker(bind=engine)
    return _readonly_session_factory


def get_async_engine() -> AsyncEngine:
    """Return the async SQLAlchemy engine singleton (asyncpg driver).

    Coexists with the sync get_engine(). statement_cache_size=0 keeps
    us PgBouncer-compatible in transaction-pooling mode.
    """
    global _async_engine
    if _async_engine is None:
        with _init_lock:
            if _async_engine is None:
                settings = get_settings()
                _validate_database_url(settings.database_url)
                async_url = _to_async_url(settings.database_url)
                # TODO: asyncpg ignores ?sslmode= in the URL; translate
                # sslmode=require → connect_args={"ssl": True} before shipping
                # to a TLS-enforced prod cluster.
                if async_url.startswith("sqlite+aiosqlite://"):
                    _async_engine = create_async_engine(async_url, echo=False)
                else:
                    connect_args: dict[str, object] = {
                        "statement_cache_size": 0,
                        "timeout": 10,
                    }
                    _async_engine = create_async_engine(
                        async_url,
                        echo=False,
                        pool_pre_ping=True,
                        pool_size=settings.db_pool_size,
                        max_overflow=settings.db_pool_max_overflow,
                        pool_timeout=settings.db_pool_timeout,
                        pool_recycle=settings.db_pool_recycle,
                        connect_args=connect_args,
                    )
                logger.info("async_engine_initialized", driver=async_url.split("://", 1)[0])
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory singleton.

    expire_on_commit=False so attributes stay accessible after
    await session.commit() in the dependency teardown.
    """
    global _async_session_factory
    if _async_session_factory is None:
        # Resolve the engine BEFORE acquiring _init_lock — get_async_engine
        # also takes _init_lock, and threading.Lock is not re-entrant.
        engine = get_async_engine()
        with _init_lock:
            if _async_session_factory is None:
                _async_session_factory = async_sessionmaker(
                    bind=engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
    return _async_session_factory
