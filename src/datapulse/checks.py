"""Shared health-check helpers.

Extracted from ``api.routes.health`` to break the cyclic import between
``health`` and ``scheduler`` — both modules now import from here.
"""

import time

import structlog
from sqlalchemy import text

from datapulse.api.deps import get_engine

logger = structlog.get_logger()


def check_db() -> dict:
    """Ping PostgreSQL and return status + latency."""
    try:
        t0 = time.monotonic()
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        logger.exception("Database health check failed")
        return {"status": "error", "error": "internal_error"}


def check_redis() -> dict:
    """Ping Redis and return status + latency."""
    try:
        from datapulse.cache import get_redis_client

        client = get_redis_client()
        if client is None:
            return {"status": "disabled"}
        t0 = time.monotonic()
        client.ping()
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        logger.exception("Redis health check failed")
        return {"status": "error", "error": "internal_error"}
