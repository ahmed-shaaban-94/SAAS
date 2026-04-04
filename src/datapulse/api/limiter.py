"""Rate limiter configuration for the API.

Uses Redis as storage backend when available for global (cross-worker)
rate limiting.  Falls back to in-memory storage in dev mode.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


def _make_limiter() -> Limiter:
    """Create a Limiter backed by Redis when ``REDIS_URL`` is configured."""
    try:
        from datapulse.core.config import get_settings

        redis_url = get_settings().redis_url
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("limiter_config_error: %s — falling back to memory", exc)
        redis_url = ""

    storage_uri = redis_url if redis_url else "memory://"
    return Limiter(
        key_func=get_remote_address,
        default_limits=["60/minute"],
        storage_uri=storage_uri,
    )


limiter = _make_limiter()
