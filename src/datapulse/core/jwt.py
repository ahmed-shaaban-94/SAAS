"""JWT verification using Auth0 JWKS endpoint.

Fetches public keys from the Auth0 JWKS endpoint, caches them with a TTL,
and verifies incoming Bearer tokens.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
import structlog
from fastapi import HTTPException

from datapulse.config import Settings, get_settings

_JWKS_RETRY_DELAYS: tuple[float, ...] = (0.5, 1.0, 2.0)  # seconds between attempts

logger = structlog.get_logger()

# Module-level JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: float = 0.0
_JWKS_CACHE_TTL: int = 3600  # 1 hour (keys rarely rotate; miss triggers forced refresh)


def _fetch_jwks(settings: Settings) -> dict[str, Any]:
    """Fetch JWKS from Auth0, with in-memory TTL cache and retry backoff.

    Attempts up to 3 times (delays: 1s, 2s, 4s) on network/timeout errors.
    HTTP 4xx responses are not retried — they indicate a configuration error.
    Returns stale cache as a last resort before raising 503.
    """
    global _jwks_cache, _jwks_cache_time

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cache_time) < _JWKS_CACHE_TTL:
        return _jwks_cache

    jwks_url = settings.auth0_jwks_url
    last_exc: Exception | None = None

    for attempt, delay in enumerate((*_JWKS_RETRY_DELAYS, None), start=1):  # type: ignore[arg-type]
        try:
            resp = httpx.get(jwks_url, timeout=5.0)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_time = time.monotonic()
            logger.info("jwks_fetched", url=jwks_url, attempt=attempt)
            return _jwks_cache
        except httpx.HTTPStatusError as exc:
            # 4xx errors are not transient — don't retry
            logger.error("jwks_fetch_http_error", url=jwks_url, status=exc.response.status_code)
            last_exc = exc
            break
        except Exception as exc:
            logger.warning(
                "jwks_fetch_network_error", url=jwks_url, attempt=attempt, error=str(exc)
            )
            last_exc = exc
            if delay is not None:
                time.sleep(delay)

    logger.error("jwks_fetch_failed", url=jwks_url, error=str(last_exc))
    # Return stale cache if available (better than hard failure)
    if _jwks_cache:
        logger.warning("jwks_using_stale_cache")
        return _jwks_cache
    raise HTTPException(
        status_code=503,
        detail="Authentication service unavailable",
    ) from last_exc


def _get_signing_key(token: str, settings: Settings) -> jwt.PyJWK:
    """Extract the signing key from JWKS that matches the token's kid."""
    jwks_data = _fetch_jwks(settings)

    try:
        jwk_set = jwt.PyJWKSet.from_dict(jwks_data)
    except jwt.PyJWKSetError as exc:
        logger.error("jwks_parse_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        ) from exc

    # Decode header to get kid
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise HTTPException(status_code=401, detail="Invalid token format") from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing key ID")

    # Find matching key
    for key in jwk_set.keys:
        if key.key_id == kid:
            return key

    # Key not found — maybe keys rotated; clear cache and retry once
    global _jwks_cache_time
    _jwks_cache_time = 0.0
    jwks_data = _fetch_jwks(settings)

    try:
        jwk_set = jwt.PyJWKSet.from_dict(jwks_data)
    except jwt.PyJWKSetError as exc:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        ) from exc

    for key in jwk_set.keys:
        if key.key_id == kid:
            return key

    raise HTTPException(status_code=401, detail="Token signing key not found")


def verify_jwt(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and verify a JWT token using Auth0 JWKS keys.

    Returns the decoded claims dict on success.
    Raises HTTPException(401) on invalid/expired tokens.
    Raises HTTPException(503) if Auth0 is unreachable.
    """
    if settings is None:
        settings = get_settings()

    signing_key = _get_signing_key(token, settings)

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.auth0_issuer_url,
            audience=settings.auth0_audience or None,
            options={
                "verify_exp": True,
                "verify_aud": bool(settings.auth0_audience),
                "verify_iss": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(status_code=401, detail="Invalid token issuer") from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(status_code=401, detail="Invalid token audience") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("jwt_validation_failed", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    # Verify azp (authorized party) matches expected client if present
    azp = claims.get("azp")
    if azp and azp != settings.auth0_client_id:
        raise HTTPException(status_code=401, detail="Invalid token client")

    return claims


def clear_jwks_cache() -> None:
    """Clear the JWKS cache (useful for testing)."""
    global _jwks_cache, _jwks_cache_time
    _jwks_cache = {}
    _jwks_cache_time = 0.0
