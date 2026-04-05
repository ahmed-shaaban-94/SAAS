"""Redis cache module with graceful degradation.

If Redis is unavailable, all operations silently fall through
so the application continues using direct database queries.
"""

from __future__ import annotations

import contextvars
import json
import time
from typing import Any

import structlog

from datapulse.config import get_settings

logger = structlog.get_logger()

# Context variable holding the current tenant_id.  Set by ``get_tenant_session``
# in ``datapulse.api.deps`` so that cache keys are automatically scoped per
# tenant without requiring explicit passing through every service method.
current_tenant_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_tenant_id", default=""
)

_redis_client = None
_last_attempt: float = 0
_RETRY_INTERVAL = 15  # seconds before retrying a failed connection


def get_redis_client():
    """Return the shared Redis client, or None if unavailable.

    Retries connection after ``_RETRY_INTERVAL`` seconds if the previous
    attempt failed, allowing recovery from transient startup issues.
    """
    global _redis_client, _last_attempt

    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None
            # fall through to reconnect

    now = time.monotonic()
    if _last_attempt and (now - _last_attempt) < _RETRY_INTERVAL:
        return None

    _last_attempt = now
    settings = get_settings()
    if not settings.redis_url:
        logger.info("redis_disabled", detail="REDIS_URL is empty — caching disabled")
        return None

    try:
        import redis

        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        client.ping()
        _redis_client = client
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))

    return _redis_client


_CACHE_MISS = object()


def cache_get(key: str) -> Any | None:
    """Get a value from cache. Returns None on miss or error."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            logger.debug("cache_miss", key=key)
            return None
        logger.debug("cache_hit", key=key)
        return json.loads(raw)
    except Exception as exc:
        logger.error("cache_get_error", key=key, error=str(exc))
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
        logger.error("cache_set_error", key=key, error=str(exc))


def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a glob pattern. Returns count deleted.

    Uses SCAN (non-blocking) instead of KEYS to avoid blocking Redis.
    """
    client = get_redis_client()
    if client is None:
        return 0
    try:
        keys = list(client.scan_iter(match=pattern, count=100))
        if keys:
            deleted = client.delete(*keys)
            logger.info("cache_invalidated", pattern=pattern, count=deleted)
            return deleted
        return 0
    except Exception as exc:
        logger.error("cache_invalidate_error", pattern=pattern, error=str(exc))
        return 0
