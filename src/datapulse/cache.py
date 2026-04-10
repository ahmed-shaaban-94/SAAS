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

try:
    import redis as _redis_mod

    _REDIS_CONN_ERRORS: tuple[type[BaseException], ...] = (
        _redis_mod.ConnectionError,
        _redis_mod.TimeoutError,
        OSError,
    )
    _REDIS_OP_ERRORS: tuple[type[BaseException], ...] = (
        _redis_mod.RedisError,
        json.JSONDecodeError,
        OSError,
    )
    _REDIS_WRITE_ERRORS: tuple[type[BaseException], ...] = (
        _redis_mod.RedisError,
        TypeError,
        OSError,
    )
except ImportError:  # pragma: no cover
    _redis_mod = None  # type: ignore[assignment]
    _REDIS_CONN_ERRORS = (OSError,)
    _REDIS_OP_ERRORS = (OSError,)
    _REDIS_WRITE_ERRORS = (OSError,)

from datapulse.config import get_settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prometheus cache metrics (optional — degrades gracefully if not installed)
# ---------------------------------------------------------------------------
try:
    from prometheus_client import Counter

    _cache_hits = Counter(
        "cache_hits_total",
        "Total number of Redis cache hits",
        ["key_prefix"],
    )
    _cache_misses = Counter(
        "cache_misses_total",
        "Total number of Redis cache misses",
        ["key_prefix"],
    )
    _PROMETHEUS_ENABLED = True
except ImportError:  # pragma: no cover
    _PROMETHEUS_ENABLED = False


def _record_hit(key: str) -> None:
    if _PROMETHEUS_ENABLED:
        prefix = key.split(":")[0] if ":" in key else key
        _cache_hits.labels(key_prefix=prefix).inc()


def _record_miss(key: str) -> None:
    if _PROMETHEUS_ENABLED:
        prefix = key.split(":")[0] if ":" in key else key
        _cache_misses.labels(key_prefix=prefix).inc()


# Context variable holding the current tenant_id.  Set by ``get_tenant_session``
# in ``datapulse.api.deps`` so that cache keys are automatically scoped per
# tenant without requiring explicit passing through every service method.
current_tenant_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_tenant_id", default=""
)

_redis_client = None
_last_attempt: float = 0


def get_redis_client():
    """Return the shared Redis client, or None if unavailable.

    Retries connection after ``settings.redis_retry_interval`` seconds
    if the previous attempt failed, allowing recovery from transient
    startup issues.
    """
    global _redis_client, _last_attempt

    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except _REDIS_CONN_ERRORS:
            _redis_client = None
            # fall through to reconnect

    settings = get_settings()
    now = time.monotonic()
    if _last_attempt and (now - _last_attempt) < settings.redis_retry_interval:
        return None

    _last_attempt = now
    if not settings.redis_url:
        logger.info("redis_disabled", detail="REDIS_URL is empty — caching disabled")
        return None

    try:
        import redis

        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.redis_socket_timeout,
            socket_timeout=settings.redis_socket_timeout,
            retry_on_timeout=True,
        )
        client.ping()
        _redis_client = client
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
    except _REDIS_CONN_ERRORS as exc:
        logger.warning("redis_unavailable", error=str(exc))

    return _redis_client


_CACHE_MISS = object()


def cache_get(key: str) -> Any | None:
    """Get a value from cache. Returns None on miss or error."""
    client = get_redis_client()
    if client is None:
        _record_miss(key)
        return None
    try:
        raw = client.get(key)
        if raw is None:
            logger.debug("cache_miss", key=key)
            _record_miss(key)
            return None
        logger.debug("cache_hit", key=key)
        _record_hit(key)
        return json.loads(raw)
    except _REDIS_OP_ERRORS as exc:
        logger.error("cache_get_error", key=key, error=str(exc))
        _record_miss(key)
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
    except _REDIS_WRITE_ERRORS as exc:
        logger.error("cache_set_error", key=key, error=str(exc))


def cache_get_many(keys: list[str]) -> dict[str, Any]:
    """Fetch multiple cache keys in a single Redis PIPELINE round-trip.

    Returns a dict mapping each key to its deserialized value.  Missing keys
    and individual deserialization errors are silently omitted so callers can
    treat this as a best-effort pre-warm.

    Example::

        results = cache_get_many([key_a, key_b, key_c])
        val_a = results.get(key_a)   # None on miss
    """
    if not keys:
        return {}

    client = get_redis_client()
    if client is None:
        for key in keys:
            _record_miss(key)
        return {}

    try:
        pipe = client.pipeline(transaction=False)
        for key in keys:
            pipe.get(key)
        raw_values: list[str | None] = pipe.execute()

        result: dict[str, Any] = {}
        for key, raw in zip(keys, raw_values, strict=False):
            if raw is None:
                logger.debug("cache_miss", key=key)
                _record_miss(key)
            else:
                try:
                    result[key] = json.loads(raw)
                    logger.debug("cache_hit", key=key)
                    _record_hit(key)
                except json.JSONDecodeError as exc:
                    logger.error("cache_get_many_decode_error", key=key, error=str(exc))
                    _record_miss(key)
        return result
    except _REDIS_OP_ERRORS as exc:
        logger.error("cache_get_many_error", keys=keys, error=str(exc))
        for key in keys:
            _record_miss(key)
        return {}


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
    except _REDIS_OP_ERRORS as exc:
        logger.error("cache_invalidate_error", pattern=pattern, error=str(exc))
        return 0


_VERSION_KEY = "dp:v:current"


def cache_bump_version(run_id: str) -> None:
    """Bump the global cache version to the given pipeline run_id.

    All analytics cache keys embed the current version, so bumping it
    effectively orphans all existing cache entries — they expire via TTL
    without any O(N) SCAN invalidation.
    """
    client = get_redis_client()
    if client is None:
        logger.warning("cache_bump_version_skipped", reason="redis_unavailable", run_id=run_id)
        return
    try:
        client.set(_VERSION_KEY, run_id)
        logger.info("cache_version_bumped", run_id=run_id)
    except _REDIS_OP_ERRORS as exc:
        logger.error("cache_bump_version_error", run_id=run_id, error=str(exc))


def get_cache_version() -> str:
    """Return the current pipeline run_id (cache version), or 'v0' if unset."""
    client = get_redis_client()
    if client is None:
        return "v0"
    try:
        version = client.get(_VERSION_KEY)
        return version if version else "v0"
    except _REDIS_OP_ERRORS:
        return "v0"
