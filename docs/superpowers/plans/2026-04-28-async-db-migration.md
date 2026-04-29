# Async SQLAlchemy + asyncpg Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `src/datapulse/core/db.py` and `src/datapulse/core/db_session.py` from synchronous SQLAlchemy + psycopg2 to fully async SQLAlchemy 2.0+ with the `asyncpg` driver, expose an async `get_db` FastAPI dependency, and migrate one cohesive vertical slice (the `health` + `leads` + `branding` routes) end-to-end as proof of pattern. The remaining 100+ sync repositories keep working through a coexistence shim until they are migrated in follow-up PRs.

**Architecture:** Sync and async engines coexist behind two parallel singletons (`get_engine` / `get_async_engine`) so the migration ships incrementally without breaking the 116 files that still import the sync session. The async stack uses `create_async_engine("postgresql+asyncpg://...")` with `statement_cache_size=0` (PgBouncer-compatible), an `async_sessionmaker(expire_on_commit=False)`, and an `async def get_db()` dependency that mirrors `get_tenant_session` semantics (RLS `SET LOCAL app.tenant_id`, statement_timeout, commit/rollback/close). Uvicorn workers under Gunicorn already drive the asyncio loop — no worker-class change needed.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0 (`>=2.0,<3` already pinned), `asyncpg>=0.29`, FastAPI, `pytest-asyncio>=0.23` (already pinned), `aiosqlite>=0.19` (new, unit tests only), Gunicorn + UvicornWorker.

**Spec:** N/A — change is mechanical / scoped to the dependency layer; design constraints captured inline.

---

## File Map

| Path | Action | Responsibility |
|------|--------|----------------|
| `pyproject.toml` | Edit | Add `asyncpg>=0.29,<1`, `aiosqlite>=0.19,<1` (test extra) |
| `src/datapulse/core/db.py` | Edit | Add `get_async_engine` + `get_async_session_factory` next to existing sync singletons |
| `src/datapulse/core/db_session.py` | Edit | Add `async_tenant_session` async context manager next to the sync one |
| `src/datapulse/core/auth.py` | Edit | Add `get_tenant_session_async` (async dep) + `AsyncSessionDep` alias |
| `src/datapulse/api/deps.py` | Edit | Re-export `get_tenant_session_async`, `AsyncSessionDep`, `get_async_session_factory` |
| `src/datapulse/api/routes/health.py` | Edit | Migrate `/health/db` to `AsyncSession` |
| `src/datapulse/api/routes/leads.py` | Edit | Migrate `/leads` POST + GET to async + `AsyncSession` |
| `src/datapulse/leads/repository.py` | Edit | Convert `LeadRepository` to async (`async def`, `await session.execute(...)`) |
| `src/datapulse/leads/service.py` | Edit | Convert `LeadService` to async to mirror repository |
| `src/datapulse/api/deps.py` (factories) | Edit | `get_lead_service` becomes `async def` returning the async service |
| `tests/test_async_db.py` | Create | Unit tests for `get_async_engine`, `get_async_session_factory`, `async_tenant_session` (uses `aiosqlite`) |
| `tests/test_async_db_integration.py` | Create | Integration test against real Postgres: RLS via async session, statement_timeout enforced |
| `tests/test_leads_async.py` | Create | Unit + endpoint tests for the migrated leads route (async TestClient) |
| `tests/conftest.py` | Edit | Add `event_loop` policy + `async_test_session` fixture |
| `gunicorn.conf.py` | Verify only | Confirm `uvicorn.workers.UvicornWorker` already drives asyncio — document, no change |

Files **NOT** touched in this plan (deferred to follow-ups):
- All 100+ sync repositories under `src/datapulse/` keep using `Depends(get_tenant_session)` and sync `Session`.
- `src/datapulse/scheduler/`, `src/datapulse/bronze/`, `src/datapulse/control_center/` — use `tenant_session()` sync context manager.
- `src/datapulse/brain/db.py`, `src/datapulse/graph/mcp_server.py` — separate engines, out of scope.

---

## Preconditions

- Local stack running: `docker compose up -d postgres api` (PostgreSQL 16 reachable on `127.0.0.1:5432`).
- `DATABASE_URL` exported with the `postgresql://` prefix (the new code rewrites it to `postgresql+asyncpg://` internally).
- `DB_READER_PASSWORD` set if the reader role is reachable (replica path stays sync in this plan — out of scope).
- `pytest -m unit -x -q` is green on `main` before starting.

---

## Task 1: Add `asyncpg` + async engine/session singletons (RED → GREEN)

Adds the async stack alongside the existing sync stack. The two coexist; nothing else moves yet. Tests are written first against `aiosqlite` so they fail until the new code lands.

**Files:**
- Edit: `pyproject.toml`
- Create: `tests/test_async_db.py`
- Edit: `src/datapulse/core/db.py`

- [ ] **Step 1.1: Add `asyncpg` + `aiosqlite` deps to `pyproject.toml`**

In the `[project] dependencies` array, append after the existing `psycopg2-binary` line:

```toml
    "asyncpg>=0.29,<1",
```

In `[project.optional-dependencies].test` (find the block that already lists `pytest-asyncio`), append:

```toml
    "aiosqlite>=0.19,<1",
```

Run:

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
pip install -e .[test]
```

Expected output: ends with `Successfully installed ... asyncpg-0.29.x ... aiosqlite-0.19.x`.

- [ ] **Step 1.2: Write failing tests in `tests/test_async_db.py`**

```python
"""Unit tests for async engine + session singletons.

Uses aiosqlite to keep the suite fast and DB-free. Real-Postgres
behaviour is covered by tests/test_async_db_integration.py.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from datapulse.core import db as db_module

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_async_singletons(monkeypatch):
    """Each test gets fresh singletons so URL rewrites don't leak."""
    monkeypatch.setattr(db_module, "_async_engine", None, raising=False)
    monkeypatch.setattr(db_module, "_async_session_factory", None, raising=False)
    yield
    monkeypatch.setattr(db_module, "_async_engine", None, raising=False)
    monkeypatch.setattr(db_module, "_async_session_factory", None, raising=False)


def _patch_settings(monkeypatch, url: str) -> None:
    class _S:
        database_url = url
        database_replica_url = ""
        db_pool_size = 5
        db_pool_max_overflow = 5
        db_pool_timeout = 10
        db_pool_recycle = 1800

    monkeypatch.setattr(db_module, "get_settings", lambda: _S())
    # validate_database_url checks SENTRY_ENVIRONMENT — keep dev so sslmode isn't required
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "development")


def test_postgresql_url_rewritten_to_asyncpg(monkeypatch):
    _patch_settings(monkeypatch, "postgresql://u:p@h:5432/d")
    engine = db_module.get_async_engine()
    assert isinstance(engine, AsyncEngine)
    # SQLAlchemy normalises the URL string; the driver is what matters.
    assert engine.url.drivername == "postgresql+asyncpg"


def test_asyncpg_url_passes_through(monkeypatch):
    _patch_settings(monkeypatch, "postgresql+asyncpg://u:p@h:5432/d")
    engine = db_module.get_async_engine()
    assert engine.url.drivername == "postgresql+asyncpg"


def test_async_engine_is_singleton(monkeypatch):
    _patch_settings(monkeypatch, "postgresql://u:p@h:5432/d")
    assert db_module.get_async_engine() is db_module.get_async_engine()


def test_async_session_factory_returns_async_sessionmaker(monkeypatch):
    _patch_settings(monkeypatch, "postgresql://u:p@h:5432/d")
    factory = db_module.get_async_session_factory()
    assert isinstance(factory, async_sessionmaker)


@pytest.mark.asyncio
async def test_async_session_can_execute_against_sqlite(monkeypatch):
    """Smoke: async engine + session work end-to-end against aiosqlite."""
    _patch_settings(monkeypatch, "sqlite+aiosqlite:///:memory:")
    factory = db_module.get_async_session_factory()
    async with factory() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
```

Run:

```bash
pytest tests/test_async_db.py -x -q
```

Expected output (RED): `ImportError: cannot import name 'get_async_engine'` or similar — 5 errors / 1 collection failure.

- [ ] **Step 1.3: Implement async singletons in `src/datapulse/core/db.py`**

Add these imports near the top of `src/datapulse/core/db.py` (next to the existing `from sqlalchemy import create_engine` block):

```python
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
```

Add new module-level singletons next to the existing `_engine`, `_session_factory` block:

```python
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
```

Add a private URL-rewrite helper above `get_engine`:

```python
def _to_async_url(url: str) -> str:
    """Rewrite a sync DSN to the async asyncpg driver.

    ``postgresql://`` and ``postgresql+psycopg2://`` both map to
    ``postgresql+asyncpg://``. Everything else (sqlite+aiosqlite,
    already-async URLs) is returned unchanged.
    """
    if url.startswith("postgresql+asyncpg://") or url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url
```

Add `get_async_engine` after `get_engine`:

```python
def get_async_engine() -> AsyncEngine:
    """Return the async SQLAlchemy engine singleton (asyncpg driver).

    Coexists with the sync ``get_engine()`` so the migration can ship
    incrementally. ``statement_cache_size=0`` keeps us PgBouncer-compatible
    in transaction-pooling mode (asyncpg's prepared statement cache is
    incompatible with PgBouncer transaction pooling).
    """
    global _async_engine
    if _async_engine is None:
        with _init_lock:
            if _async_engine is None:
                settings = get_settings()
                _validate_database_url(settings.database_url)
                async_url = _to_async_url(settings.database_url)
                connect_args: dict[str, object] = {}
                if async_url.startswith("postgresql+asyncpg://"):
                    # PgBouncer-compatibility (transaction pooling): disable
                    # asyncpg's per-connection prepared statement cache.
                    connect_args["statement_cache_size"] = 0
                    # TCP-level connect timeout — mirrors sync engine's
                    # connect_timeout=10 so async startup paths can't hang
                    # indefinitely if Postgres is briefly unreachable.
                    connect_args["timeout"] = 10
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

    ``expire_on_commit=False`` so attributes stay accessible after
    ``await session.commit()`` (FastAPI handlers commonly read fields off
    the returned ORM instance after the commit happens inside the
    dependency teardown).
    """
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        with _init_lock:
            if _async_session_factory is None:
                _async_session_factory = async_sessionmaker(
                    bind=engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
    return _async_session_factory
```

Run:

```bash
pytest tests/test_async_db.py -x -q
```

Expected output (GREEN): `5 passed`.

- [ ] **Step 1.4: Verify formatting + lint + commit**

```bash
ruff format src/datapulse/core/db.py tests/test_async_db.py
ruff check src/datapulse/core/db.py tests/test_async_db.py
git add pyproject.toml src/datapulse/core/db.py tests/test_async_db.py
git commit -m "feat(db): add async SQLAlchemy engine + session factory alongside sync"
```

Expected output: `ruff check ... All checks passed!` then `git commit` summary `3 files changed`.

---

## Task 2: Add `async_tenant_session` context manager + async tenant dependency

Mirrors the sync `tenant_session()` context manager and the sync `get_tenant_session` FastAPI dep — same semantics (RLS `SET LOCAL`, statement_timeout, commit/rollback/close), async transport.

**Files:**
- Edit: `src/datapulse/core/db_session.py`
- Edit: `src/datapulse/core/auth.py`
- Edit: `src/datapulse/api/deps.py`
- Create: `tests/test_async_db_integration.py`

- [ ] **Step 2.1: Add `async_tenant_session` to `src/datapulse/core/db_session.py`**

Add imports near the top (next to the existing `Generator` import):

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from datapulse.core.db import get_async_session_factory
```

Add this function at the bottom of the file:

```python
@asynccontextmanager
async def async_tenant_session(
    tenant_id: str | int,
    *,
    timeout_s: int = 30,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a tenant-scoped ``AsyncSession``.

    Mirrors the sync ``tenant_session()``: commits on clean exit, rolls
    back on any exception, always closes. ``app.tenant_id`` is set via a
    parameterised query (no f-string interpolation) so a hostile tenant
    id cannot escape the SET LOCAL statement.
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
        log.exception("async_tenant_session_error", tenant_id=tid)
        await session.rollback()
        raise
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")
```

- [ ] **Step 2.2: Add `get_tenant_session_async` + `AsyncSessionDep` to `src/datapulse/core/auth.py`**

Add imports next to the existing SQLAlchemy imports:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from datapulse.core.db import get_async_session_factory
```

Add this function after `get_tenant_session_readonly` (around line 390, before the `SessionDep` aliases):

```python
async def get_tenant_session_async(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> AsyncGenerator[AsyncSession, None]:
    """Async equivalent of :func:`get_tenant_session`.

    Same RLS contract: ``SET LOCAL app.tenant_id`` + 30 s statement_timeout
    + commit/rollback/close in the dependency teardown. Use this for new
    async route handlers; existing sync handlers continue to use
    :func:`get_tenant_session`.
    """
    tenant_id = user["tenant_id"]
    current_tenant_id.set(str(tenant_id))
    structlog.contextvars.bind_contextvars(tenant_id=str(tenant_id))
    factory = get_async_session_factory()
    session = factory()
    try:
        await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        await session.execute(text("SET LOCAL statement_timeout = '30s'"))
        yield session
        await session.commit()
    except SQLAlchemyError:
        _db_logger.exception(
            "db_session_error", session_type="tenant_async", tenant_id=str(tenant_id)
        )
        await session.rollback()
        raise
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")
```

Add the new alias next to `SessionDep`/`SessionDepReadOnly`:

```python
AsyncSessionDep = Annotated[AsyncSession, Depends(get_tenant_session_async)]
```

- [ ] **Step 2.3: Re-export from `src/datapulse/api/deps.py`**

Find the existing block:

```python
from datapulse.core.auth import (  # noqa: F401 (re-exported for routes + tests)
    CurrentUser,
    SessionDep,
    SessionDepReadOnly,
    UserClaims,
    get_current_user,
    get_tenant_session,
    get_tenant_session_readonly,
    require_api_key,
)
```

Replace it with (alphabetical, adding two new names):

```python
from datapulse.core.auth import (  # noqa: F401 (re-exported for routes + tests)
    AsyncSessionDep,
    CurrentUser,
    SessionDep,
    SessionDepReadOnly,
    UserClaims,
    get_current_user,
    get_tenant_session,
    get_tenant_session_async,
    get_tenant_session_readonly,
    require_api_key,
)
```

Find:

```python
from datapulse.core.db import (  # noqa: F401 (get_engine re-exported for health.py)
    get_engine,
    get_session_factory,
)
```

Replace with:

```python
from datapulse.core.db import (  # noqa: F401 (get_engine re-exported for health.py)
    get_async_engine,
    get_async_session_factory,
    get_engine,
    get_session_factory,
)
```

- [ ] **Step 2.4: Write `tests/test_async_db_integration.py`**

```python
"""Integration tests for the async DB stack against real Postgres.

Skipped when localhost:5432 is not reachable — same pattern as
test_rls_db_integration.py.
"""

from __future__ import annotations

import os
import socket

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _db_is_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


requires_real_db = pytest.mark.skipif(
    not _db_is_reachable(), reason="Real PostgreSQL at localhost:5432 not reachable."
)


@requires_real_db
@pytest.mark.asyncio
async def test_async_tenant_session_sets_rls_tenant_id():
    from datapulse.core.db_session import async_tenant_session

    async with async_tenant_session(42) as session:
        result = await session.execute(text("SHOW app.tenant_id"))
        assert result.scalar_one() == "42"


@requires_real_db
@pytest.mark.asyncio
async def test_async_tenant_session_sets_statement_timeout():
    from datapulse.core.db_session import async_tenant_session

    async with async_tenant_session(1, timeout_s=7) as session:
        result = await session.execute(text("SHOW statement_timeout"))
        assert result.scalar_one() == "7s"


@requires_real_db
@pytest.mark.asyncio
async def test_async_tenant_session_rolls_back_on_exception():
    """An exception inside the block must trigger ROLLBACK, not COMMIT."""
    from datapulse.core.db_session import async_tenant_session

    with pytest.raises(RuntimeError, match="boom"):
        async with async_tenant_session(1) as session:
            await session.execute(text("SELECT 1"))
            raise RuntimeError("boom")
```

Run (skips automatically if no Postgres):

```bash
pytest tests/test_async_db_integration.py -x -q
```

Expected output (with Postgres up): `3 passed`. Expected output (without Postgres): `3 skipped`.

- [ ] **Step 2.5: Re-run unit suite + lint + commit**

```bash
ruff format src/datapulse/core/db_session.py src/datapulse/core/auth.py src/datapulse/api/deps.py tests/test_async_db_integration.py
ruff check src/datapulse/core/db_session.py src/datapulse/core/auth.py src/datapulse/api/deps.py tests/test_async_db_integration.py
pytest -m unit -x -q
git add src/datapulse/core/db_session.py src/datapulse/core/auth.py src/datapulse/api/deps.py tests/test_async_db_integration.py
git commit -m "feat(db): add async_tenant_session context manager + get_tenant_session_async dep"
```

Expected output: ruff clean; pytest unit suite green (no count regression vs. pre-change baseline); commit summary `4 files changed`.

---

## Task 3: Migrate the leads vertical slice to async (proof of pattern)

The leads route is the smallest cohesive slice that exercises the full stack: public unauthenticated endpoint → service → repository → DB. Migrating it end-to-end validates the async pattern that the remaining 100+ files will follow in subsequent PRs.

**Files:**
- Edit: `src/datapulse/leads/repository.py`
- Edit: `src/datapulse/leads/service.py`
- Edit: `src/datapulse/api/routes/leads.py`
- Edit: `src/datapulse/api/deps.py` (the `get_lead_service` factory)
- Edit: `src/datapulse/core/auth.py` (add `get_plain_session_async`)
- Create: `tests/test_leads_async.py`

- [ ] **Step 3.1: Add `get_plain_session_async` to `src/datapulse/core/auth.py`**

`/leads` is public (no auth, no tenant). Add this helper next to `get_tenant_session_async`:

```python
async def get_plain_session_async() -> AsyncGenerator[AsyncSession, None]:
    """Async plain (no-tenant) session for public endpoints.

    Mirrors :func:`datapulse.api.deps.get_plain_session` (sync). Statement
    timeout is set to 30 s — the same defence-in-depth value the sync
    helper uses.
    """
    factory = get_async_session_factory()
    session = factory()
    try:
        await session.execute(text("SET LOCAL statement_timeout = '30s'"))
        yield session
        await session.commit()
    except SQLAlchemyError:
        _db_logger.exception("db_session_error", session_type="plain_async")
        await session.rollback()
        raise
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()
```

- [ ] **Step 3.2: Convert `src/datapulse/leads/repository.py` to async**

Read the current file first. The migration pattern is mechanical — apply each transformation throughout:

| Sync | Async |
|------|-------|
| `from sqlalchemy.orm import Session` | `from sqlalchemy.ext.asyncio import AsyncSession` |
| `def __init__(self, session: Session):` | `def __init__(self, session: AsyncSession):` |
| `def create(...) -> Lead:` | `async def create(...) -> Lead:` |
| `self.session.execute(stmt)` | `await self.session.execute(stmt)` |
| `self.session.scalar(stmt)` | `await self.session.scalar(stmt)` |
| `result.scalars().all()` | `result.scalars().all()` *(unchanged — Result is sync once awaited)* |
| `self.session.add(obj)` | `self.session.add(obj)` *(unchanged — `add` is sync)* |
| `self.session.flush()` | `await self.session.flush()` |
| `self.session.refresh(obj)` | `await self.session.refresh(obj)` |
| `self.session.commit()` | *remove* — commit happens in the dependency teardown |

Edit `src/datapulse/leads/repository.py` accordingly. Keep all SQL / business logic identical.

- [ ] **Step 3.3: Convert `src/datapulse/leads/service.py` to async**

Mirror the repository — every method that calls a now-async repo method becomes `async def` and `await`s. The service should not import `Session` / `AsyncSession` directly; it accepts a `LeadRepository` instance.

- [ ] **Step 3.4: Update factory in `src/datapulse/api/deps.py`**

Find:

```python
def get_lead_service(
    session: Annotated[Session, Depends(get_plain_session)],
):
    from datapulse.leads.repository import LeadRepository
    from datapulse.leads.service import LeadService

    return LeadService(LeadRepository(session))
```

Replace with:

```python
def get_lead_service_async(
    session: Annotated[AsyncSession, Depends(get_plain_session_async)],
):
    from datapulse.leads.repository import LeadRepository
    from datapulse.leads.service import LeadService

    return LeadService(LeadRepository(session))
```

Add at the top of the file (where the other auth/session imports live):

```python
from datapulse.core.auth import get_plain_session_async  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession
```

Keep the sync `get_lead_service` function present as well — but mark it deprecated so other callers can migrate at their own pace:

```python
def get_lead_service(
    session: Annotated[Session, Depends(get_plain_session)],
):
    """Deprecated — use ``get_lead_service_async``. Kept for unmigrated callers."""
    from datapulse.leads.repository import LeadRepository  # noqa: PLC0415
    from datapulse.leads.service import LeadService  # noqa: PLC0415

    # Sync wrapper for any caller still on the sync stack — both the repo
    # and service are now async, so this path is intentionally dead. Raises
    # to surface stale wiring loudly instead of silently producing a
    # never-awaited coroutine.
    raise RuntimeError(
        "get_lead_service is deprecated — switch the route to get_lead_service_async"
    )
```

- [ ] **Step 3.5: Update `src/datapulse/api/routes/leads.py`**

Read the file. For every route handler:

1. Change `def` → `async def`.
2. Change `service: LeadService = Depends(get_lead_service)` → `service: LeadService = Depends(get_lead_service_async)`.
3. Every `service.create(...)` / `service.list(...)` call gets prefixed with `await`.

- [ ] **Step 3.6: Write `tests/test_leads_async.py`**

```python
"""Async tests for the migrated leads vertical."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_leads_repository_create_awaits_session():
    """LeadRepository.create must await session.execute / flush / refresh."""
    from datapulse.leads.repository import LeadRepository

    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repo = LeadRepository(session)

    payload = {"email": "x@y.com", "name": "Test", "company": "C"}
    await repo.create(**payload)

    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_leads_post_endpoint_runs_async(monkeypatch):
    """End-to-end: POST /leads goes through the async dep + service."""
    from datapulse.api.app import create_app
    from datapulse.api.deps import get_lead_service_async
    from datapulse.leads.service import LeadService

    fake_service = AsyncMock(spec=LeadService)
    fake_service.create.return_value = {"id": 1, "email": "x@y.com"}

    app = create_app()
    app.dependency_overrides[get_lead_service_async] = lambda: fake_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/leads", json={"email": "x@y.com", "name": "Test", "company": "C"}
        )

    assert resp.status_code in (200, 201)
    fake_service.create.assert_awaited_once()
```

Run:

```bash
pytest tests/test_leads_async.py -x -q
```

Expected output: `2 passed`.

- [ ] **Step 3.7: Lint + full unit suite + commit**

```bash
ruff format src/datapulse/leads/ src/datapulse/api/routes/leads.py src/datapulse/api/deps.py src/datapulse/core/auth.py tests/test_leads_async.py
ruff check src/datapulse/leads/ src/datapulse/api/routes/leads.py src/datapulse/api/deps.py src/datapulse/core/auth.py tests/test_leads_async.py
pytest -m unit -x -q
git add src/datapulse/leads/ src/datapulse/api/routes/leads.py src/datapulse/api/deps.py src/datapulse/core/auth.py tests/test_leads_async.py
git commit -m "refactor(leads): migrate leads vertical slice to async SQLAlchemy"
```

Expected output: ruff clean; pytest unit suite green; commit summary `~6 files changed`.

---

## Task 4: Migrate `/health/db` probe to async + verify Gunicorn config

The `/health/db` endpoint is the second-smallest slice and is the canary that proves the async engine is wired into the running app. Also verifies (no change required) that Gunicorn's UvicornWorker drives the asyncio loop.

**Files:**
- Edit: `src/datapulse/api/routes/health.py`
- Verify only: `gunicorn.conf.py`
- Edit: `tests/test_async_db_integration.py` (append one endpoint test)

- [ ] **Step 4.1: Migrate the DB-health probe in `src/datapulse/api/routes/health.py`**

Read the file. The DB-probe handler today calls `engine.connect()` synchronously. Replace with the async engine:

```python
from sqlalchemy import text

from datapulse.core.db import get_async_engine


@router.get("/health/db")
async def health_db() -> dict[str, str]:
    """Async DB-reachability probe.

    Returns 200 + ``{"status": "ok"}`` when a single ``SELECT 1`` round-trip
    completes within the engine's connect_timeout. Any failure raises
    ``HTTPException(503)`` so Kubernetes / DO health-checks correctly mark
    the pod unready.
    """
    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    except Exception as exc:  # noqa: BLE001 — health probe must catch all
        raise HTTPException(status_code=503, detail=f"db_unreachable: {exc!s}") from exc
    return {"status": "ok"}
```

If the file already imports `text` / `HTTPException` from elsewhere, deduplicate. Keep all other handlers in the file unchanged.

- [ ] **Step 4.2: Add an integration test for `/health/db`**

Append to `tests/test_async_db_integration.py`:

```python
@requires_real_db
@pytest.mark.asyncio
async def test_health_db_endpoint_returns_200():
    from httpx import ASGITransport, AsyncClient

    from datapulse.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/db")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 4.3: Verify `gunicorn.conf.py` (no edit expected)**

```bash
grep -n "worker_class\|UvicornWorker" C:/Users/user/Documents/GitHub/Data-Pulse/gunicorn.conf.py
```

Expected output: `worker_class = "uvicorn.workers.UvicornWorker"`. No change is required — UvicornWorker already drives the asyncio loop. Document this in the commit message.

- [ ] **Step 4.4: Run integration suite, lint, commit**

```bash
ruff format src/datapulse/api/routes/health.py tests/test_async_db_integration.py
ruff check src/datapulse/api/routes/health.py tests/test_async_db_integration.py
pytest tests/test_async_db_integration.py -x -q
pytest -m unit -x -q
git add src/datapulse/api/routes/health.py tests/test_async_db_integration.py
git commit -m "refactor(health): migrate /health/db probe to async engine; verify UvicornWorker"
```

Expected output: ruff clean; integration tests pass (or skip if no Postgres); unit suite green; commit summary `2 files changed`.

---

## Task 5: Document the migration playbook for follow-up PRs

Records the exact mechanical pattern so the remaining 100+ files can be migrated by subsequent PRs (one repository per PR) without re-deriving the recipe.

**Files:**
- Create: `docs/brain/decisions/2026-04-28-async-sqlalchemy-migration.md`

- [ ] **Step 5.1: Write the decision record**

```markdown
# Async SQLAlchemy + asyncpg migration — decision record

**Date:** 2026-04-28
**Branch of record:** fix/clerk-routing-env (this PR)
**Status:** in progress — leads + health migrated; ~115 files remain

## Why

- Sync psycopg2 + threaded workers caps p99 latency under bursty load: every
  request holds a worker thread for the full DB round-trip.
- asyncpg is the fastest Postgres driver for Python and frees the event
  loop during waits, so a single UvicornWorker can serve far more
  concurrent slow analytics queries.
- SQLAlchemy 2.0 async is mature; we already pin `sqlalchemy>=2.0,<3`.

## Coexistence strategy

- `get_engine` (sync) and `get_async_engine` (async) live side-by-side in
  `src/datapulse/core/db.py`. Same for session factories.
- `get_tenant_session` (sync) and `get_tenant_session_async` (async) live
  side-by-side in `src/datapulse/core/auth.py`.
- Each repository / route migrates in its own PR. Until a repo is migrated
  it keeps `Depends(get_tenant_session)` and a sync `Session`.

## Mechanical recipe per repository

1. `Session` → `AsyncSession` in the type hint.
2. Each method becomes `async def`.
3. `session.execute(...)` → `await session.execute(...)`.
4. `session.scalar(...)` / `session.scalars(...)` → `await session.scalar(...)` / `await session.scalars(...)`.
5. `session.flush()` → `await session.flush()`.
6. `session.refresh(obj)` → `await session.refresh(obj)`.
7. `session.commit()` → DELETE — commit happens in the dep teardown.
8. `session.add(...)` and `Result.scalars()` / `.all()` / `.first()` stay sync.
9. Service: every method that awaits the repo becomes `async def` + `await`.
10. Factory in `api/deps.py`: `Depends(get_tenant_session)` → `Depends(get_tenant_session_async)`.
11. Route handler: `def` → `async def`, prefix `service.method(...)` calls with `await`.

## PgBouncer note

`statement_cache_size=0` is mandatory in `connect_args` for asyncpg under
PgBouncer transaction-pooling mode. Encoded in `get_async_engine`.

## Out of scope this PR

- Read-replica async path (`get_tenant_session_readonly`). Stays sync.
- `tenant_session()` sync context manager used by scheduler / bronze /
  control_center — those are background jobs, not request-path.
- `src/datapulse/brain/db.py` and `graph/mcp_server.py` — separate engines.

## Rollback

The sync stack is untouched. Reverting any single migration PR rolls that
slice back without affecting others.
```

- [ ] **Step 5.2: Commit**

```bash
git add docs/brain/decisions/2026-04-28-async-sqlalchemy-migration.md
git commit -m "docs(brain): record async SQLAlchemy migration playbook"
```

Expected output: `1 file changed`.

---

## Final Verification

- [ ] **All-green check:**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
pytest -m unit -x -q
pytest -m integration -x -q   # if Postgres is up; otherwise skipped
```

Expected output: every step green; unit count ≥ pre-PR baseline + 7 new tests (5 from Task 1, 2 from Task 3); integration count ≥ pre-PR baseline + 4 new tests (3 from Task 2, 1 from Task 4) when Postgres is reachable.

- [ ] **Manual smoke (optional, requires running stack):**

```bash
docker compose up -d postgres api
curl -fsS http://localhost:8000/health/db
```

Expected output: `{"status":"ok"}`.

---

## What this PR does NOT do (deferred)

- Migrate the remaining 100+ repositories. Each gets its own PR using the
  recipe in Task 5's decision record.
- Migrate the readonly replica path. Stays sync until the primary path is
  fully async.
- Migrate background workers (scheduler, bronze loader, control_center).
  Those use `tenant_session()` sync context manager — separate work item.
- Drop `psycopg2-binary` from `pyproject.toml`. Keep until the last sync
  caller is gone.
