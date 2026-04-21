"""JWT verification — thin re-export shim.

Canonical home: :mod:`datapulse.core.jwt`. This module survives only for
backwards compatibility with callers that still do
``from datapulse.api.jwt import verify_jwt``. New code should import from
``datapulse.core.jwt`` directly. Tracked in issue #541.
"""

from datapulse.core.jwt import (
    _JWKS_CACHE_TTL,
    _JWKS_RETRY_DELAYS,
    _fetch_jwks,
    _get_signing_key,
    clear_jwks_cache,
    verify_jwt,
)

__all__ = [
    "_JWKS_CACHE_TTL",
    "_JWKS_RETRY_DELAYS",
    "_fetch_jwks",
    "_get_signing_key",
    "clear_jwks_cache",
    "verify_jwt",
]
