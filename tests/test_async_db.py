"""Unit tests for async engine + session singletons.

Uses aiosqlite to keep the suite fast and DB-free.
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
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "development")


def test_postgresql_url_rewritten_to_asyncpg(monkeypatch):
    _patch_settings(monkeypatch, "postgresql://u:p@h:5432/d")
    engine = db_module.get_async_engine()
    assert isinstance(engine, AsyncEngine)
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
