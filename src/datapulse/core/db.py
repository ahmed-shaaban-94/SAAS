"""Database engine and session factory singletons.

Provides thread-safe lazy initialization of the SQLAlchemy engine
and session factory, importable from anywhere without pulling in
FastAPI-specific dependencies.
"""

from __future__ import annotations

import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from datapulse.core.config import get_settings

logger = structlog.get_logger()
_STATEMENT_TIMEOUT_RE = re.compile(r"^\d+(?:ms|s|min|h)$")


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


def _validate_statement_timeout(statement_timeout: str | None) -> str | None:
    if statement_timeout is None:
        return None
    if not _STATEMENT_TIMEOUT_RE.match(statement_timeout):
        raise ValueError(
            "statement_timeout must look like '10s', '500ms', '5min', or '1h'",
        )
    return statement_timeout


def apply_session_locals(
    executor: Session | Connection,
    *,
    tenant_id: str | int | None = None,
    statement_timeout: str | None = "30s",
) -> None:
    """Apply tenant + timeout locals to a session/connection transaction."""
    timeout = _validate_statement_timeout(statement_timeout)
    if tenant_id is not None:
        executor.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
    if timeout is not None:
        executor.execute(text(f"SET LOCAL statement_timeout = '{timeout}'"))


@contextmanager
def session_scope(
    *,
    tenant_id: str | int | None = None,
    statement_timeout: str | None = "30s",
    session_type: str = "plain",
) -> Iterator[Session]:
    """Yield a session with consistent timeout, rollback, and close behavior."""
    tenant_id_str = str(tenant_id) if tenant_id is not None else None
    tenant_token = None
    if tenant_id_str is not None:
        from datapulse.cache import current_tenant_id

        tenant_token = current_tenant_id.set(tenant_id_str)
        structlog.contextvars.bind_contextvars(tenant_id=tenant_id_str)

    session = get_session_factory()()
    try:
        apply_session_locals(
            session,
            tenant_id=tenant_id_str,
            statement_timeout=statement_timeout,
        )
        yield session
        session.commit()
    except SQLAlchemyError:
        logger.exception(
            "db_session_error",
            session_type=session_type,
            tenant_id=tenant_id_str,
        )
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        if tenant_id_str is not None:
            from datapulse.cache import current_tenant_id

            structlog.contextvars.unbind_contextvars("tenant_id")
            if tenant_token is not None:
                current_tenant_id.reset(tenant_token)


@contextmanager
def tenant_session_scope(
    tenant_id: str | int,
    *,
    statement_timeout: str = "30s",
    session_type: str = "tenant",
) -> Iterator[Session]:
    """Yield a tenant-scoped session bound to one canonical RLS path."""
    with session_scope(
        tenant_id=tenant_id,
        statement_timeout=statement_timeout,
        session_type=session_type,
    ) as session:
        yield session


@contextmanager
def plain_session_scope(
    *,
    statement_timeout: str | None = "30s",
    session_type: str = "plain",
) -> Iterator[Session]:
    """Yield a plain session with shared timeout / rollback semantics."""
    with session_scope(
        statement_timeout=statement_timeout,
        session_type=session_type,
    ) as session:
        yield session
