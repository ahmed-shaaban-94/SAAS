"""Universal cache decorator for service methods.

Provides a ``@cached(ttl=N, prefix="...")`` decorator that wraps any
service method with Redis caching using the existing ``datapulse.cache``
module.  Cache keys are derived from the method name and arguments via
a deterministic MD5 hash.

Usage::

    class MyService:
        @cached(ttl=120, prefix="analytics")
        def get_daily_trend(self, filters: AnalyticsFilter | None = None):
            ...
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from typing import Any, TypeVar

from datapulse.cache import cache_get, cache_set
from datapulse.logging import get_logger

log = get_logger(__name__)

F = TypeVar("F")

_DEFAULT_PREFIX = "datapulse"


def _build_cache_key(prefix: str, method_name: str, args: tuple, kwargs: dict) -> str:
    """Build a deterministic cache key from method name and arguments.

    Skips ``self`` (first positional arg for bound methods) so that
    different service instances sharing the same session produce the
    same cache key for identical parameters.
    """
    # Skip 'self' — first positional argument of bound methods
    serialisable_args = args[1:] if args else ()

    parts: dict[str, Any] = {}
    for i, arg in enumerate(serialisable_args):
        if hasattr(arg, "model_dump"):
            parts[f"arg{i}"] = arg.model_dump(mode="json")
        else:
            parts[f"arg{i}"] = arg

    for k, v in kwargs.items():
        if hasattr(v, "model_dump"):
            parts[k] = v.model_dump(mode="json")
        else:
            parts[k] = v

    if parts:
        raw = json.dumps(parts, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{prefix}:{method_name}:{h}"
    return f"{prefix}:{method_name}"


def cached(ttl: int = 300, prefix: str = _DEFAULT_PREFIX):
    """Decorator that caches the return value of a service method in Redis.

    Parameters
    ----------
    ttl:
        Time-to-live in seconds.  Defaults to 300 (5 min).
    prefix:
        Key namespace prefix.  Defaults to ``"datapulse"``.

    The decorated function must return either:
    - A Pydantic model (has ``.model_dump()``), or
    - A plain dict / list / primitive that is JSON-serialisable.

    On cache hit the raw dict/list is returned (the caller is responsible
    for re-hydrating into the appropriate model if needed).
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _build_cache_key(prefix, func.__name__, args, kwargs)

            # Try cache first
            hit = cache_get(key)
            if hit is not None:
                log.debug("cache_hit", key=key)
                return hit

            # Execute the real function
            result = func(*args, **kwargs)

            # Serialise and cache
            if hasattr(result, "model_dump"):
                cache_set(key, result.model_dump(mode="json"), ttl=ttl)
            elif isinstance(result, (dict, list, int, float, str, bool)):
                cache_set(key, result, ttl=ttl)
            elif isinstance(result, tuple):
                cache_set(key, list(result), ttl=ttl)
            else:
                log.debug("cache_skip_unserializable", key=key, type=type(result).__name__)

            return result

        # Preserve the original function's signature so that FastAPI's
        # dependency injection inspects the real parameters instead of
        # seeing the wrapper's (*args, **kwargs).
        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]

        # Expose cache metadata for testing/introspection
        wrapper._cache_prefix = prefix  # type: ignore[attr-defined]
        wrapper._cache_ttl = ttl  # type: ignore[attr-defined]
        return wrapper

    return decorator
