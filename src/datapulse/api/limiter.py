"""Rate limiter configuration for the API.

Uses Redis as storage backend when available for global (cross-worker)
rate limiting.  Falls back to in-memory storage when Redis is unavailable,
dividing the limit by worker count to approximate the intended global rate.
"""

import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_log = logging.getLogger(__name__)

_REDIS_LIMIT = "60/minute"
_WORKERS = int(os.environ.get("WEB_CONCURRENCY", "4"))
_FALLBACK_LIMIT = f"{max(1, 60 // _WORKERS)}/minute"


def _make_limiter() -> Limiter:
    """Create a Limiter backed by Redis when ``REDIS_URL`` is configured.

    Falls back to in-memory storage if Redis is unavailable.  In fallback
    mode the per-process limit is divided by the worker count so that the
    effective global rate approximates the intended ``60/minute``.
    """
    redis_url = ""
    try:
        from datapulse.config import get_settings

        redis_url = get_settings().redis_url
    except (ImportError, ValueError, OSError) as exc:
        _log.warning("limiter_config_error — falling back to memory: %s", exc)

    if redis_url:
        return Limiter(
            key_func=get_remote_address,
            default_limits=[_REDIS_LIMIT],
            storage_uri=redis_url,
        )

    _log.warning(
        "limiter_redis_fallback: using in-memory storage (limit divided by %d workers): %s",
        _WORKERS,
        _FALLBACK_LIMIT,
    )
    return Limiter(
        key_func=get_remote_address,
        default_limits=[_FALLBACK_LIMIT],
        storage_uri="memory://",
    )


limiter = _make_limiter()
