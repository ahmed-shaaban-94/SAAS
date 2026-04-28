"""Shared tenant-scoped DB session helper for non-request flows.

Use this instead of calling ``get_session_factory()()`` directly in
background tasks, schedulers, loaders, and async generators. It:

  * Sets ``app.tenant_id`` via a **parameterised** query (not f-string)
    to prevent tenant-ID injection.
  * Sets ``statement_timeout`` so long-running background work doesn't
    lock the DB indefinitely.
  * Commits on clean exit, rolls back + closes on any exception, and
    always closes the session in the ``finally`` block.

Usage (sync)::

    from datapulse.core.db_session import tenant_session

    with tenant_session(tenant_id) as session:
        repo = MyRepository(session)
        result = repo.do_something()

Usage (async / manual close)::

    session = open_tenant_session(tenant_id, timeout_s=600)
    try:
        ...
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from datapulse.core.db import get_async_session_factory, get_session_factory
from datapulse.logging import get_logger

log = get_logger(__name__)


def open_tenant_session(tenant_id: str | int, *, timeout_s: int = 30) -> Session:
    """Create and configure a tenant-scoped session (caller manages lifecycle).

    Prefer the ``tenant_session()`` context manager for synchronous code.
    Use this variant only when you need to manage commit/close manually
    (e.g. inside an async generator that can't use ``with``).
    """
    tid = str(tenant_id)
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
        session.execute(text(f"SET LOCAL statement_timeout = '{int(timeout_s)}s'"))
    except Exception:
        session.close()
        raise
    structlog.contextvars.bind_contextvars(tenant_id=tid)
    return session


@contextmanager
def tenant_session(
    tenant_id: str | int,
    *,
    timeout_s: int = 30,
) -> Generator[Session, None, None]:
    """Context manager that yields a tenant-scoped SQLAlchemy session.

    Commits on clean exit, rolls back on any exception, and always closes.
    """
    tid = str(tenant_id)
    structlog.contextvars.bind_contextvars(tenant_id=tid)
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
        session.execute(text(f"SET LOCAL statement_timeout = '{int(timeout_s)}s'"))
        yield session
        session.commit()
    except SQLAlchemyError:
        log.exception("tenant_session_error", tenant_id=tid)
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")


@asynccontextmanager
async def async_tenant_session(
    tenant_id: str | int,
    *,
    timeout_s: int = 30,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a tenant-scoped AsyncSession.

    Same RLS contract as tenant_session(): SET LOCAL app.tenant_id,
    statement_timeout, commit on clean exit, rollback on exception.
    """
    tid = str(tenant_id)
    structlog.contextvars.bind_contextvars(tenant_id=tid)
    factory = get_async_session_factory()
    session = factory()
    try:
        await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
        await session.execute(text(f"SET LOCAL statement_timeout = '{int(timeout_s)}s'"))
        yield session
        await session.commit()
    except SQLAlchemyError:
        log.exception("tenant_session_error", tenant_id=tid)
        await session.rollback()
        raise
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")
