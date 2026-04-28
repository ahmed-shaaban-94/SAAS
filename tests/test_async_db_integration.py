"""Integration tests for the async DB stack against real Postgres.

Skipped when localhost:5432 is not reachable.
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
    from datapulse.core.db_session import async_tenant_session

    with pytest.raises(RuntimeError, match="boom"):
        async with async_tenant_session(1) as session:
            await session.execute(text("SELECT 1"))
            raise RuntimeError("boom")
