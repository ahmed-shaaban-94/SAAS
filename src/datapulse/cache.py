"""Redis cache module with graceful degradation.

If Redis is unavailable, all operations silently fall through
so the application continues using direct database queries.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from datapulse.config import get_settings

logger = structlog.get_logger()

_redis_client = None
_redis_checked = False


def get_redis_client():
    """Return the shared Redis client, or None if unavailable."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True

    settings = get_settings()
    if not settings.redis_url:
        logger.info("redis_disabled", detail="REDIS_URL is empty — caching disabled")
        return None

    try:
        import redis

        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis_client.ping()
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))
        _redis_client = None

    return _redis_client


def cache_get(key: str) -> Any | None:
    """Get a value from cache. Returns None on miss or error."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("cache_get_error", key=key, error=str(exc))
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Set a value in cache with optional TTL (seconds). Silently fails."""
    client = get_redis_client()
    if client is None:
        return
    if ttl is None:
        ttl = get_settings().redis_default_ttl
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("cache_set_error", key=key, error=str(exc))


def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a glob pattern. Returns count deleted."""
    client = get_redis_client()
    if client is None:
        return 0
    try:
        keys = client.keys(pattern)
        if keys:
            deleted = client.delete(*keys)
            logger.info("cache_invalidated", pattern=pattern, count=deleted)
            return deleted
        return 0
    except Exception as exc:
        logger.warning("cache_invalidate_error", pattern=pattern, error=str(exc))
        return 0
