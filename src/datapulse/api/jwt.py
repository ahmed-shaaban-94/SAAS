"""JWT verification using Keycloak JWKS endpoint.

Fetches public keys from the Keycloak OIDC well-known JWKS endpoint,
caches them with a TTL, and verifies incoming Bearer tokens.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
import structlog
from fastapi import HTTPException

from datapulse.config import Settings, get_settings

logger = structlog.get_logger()

# Module-level JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: float = 0.0
_JWKS_CACHE_TTL: int = 3600  # 1 hour (keys rarely rotate; miss triggers forced refresh)


def _fetch_jwks(settings: Settings) -> dict[str, Any]:
    """Fetch JWKS from Keycloak, with in-memory TTL cache."""
    global _jwks_cache, _jwks_cache_time

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cache_time) < _JWKS_CACHE_TTL:
        return _jwks_cache

    try:
        resp = httpx.get(settings.keycloak_jwks_url, timeout=10.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = now
        logger.info("jwks_fetched", url=settings.keycloak_jwks_url)
        return _jwks_cache
    except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
        logger.error("jwks_fetch_failed", url=settings.keycloak_jwks_url, error=str(exc))
        # Return stale cache if available (better than hard failure)
        if _jwks_cache:
            logger.warning("jwks_using_stale_cache")
            return _jwks_cache
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        ) from exc


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
    """Decode and verify a JWT token using Keycloak JWKS keys.

    Returns the decoded claims dict on success.
    Raises HTTPException(401) on invalid/expired tokens.
    Raises HTTPException(503) if Keycloak is unreachable.
    """
    if settings is None:
        settings = get_settings()

    signing_key = _get_signing_key(token, settings)

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.keycloak_token_issuer_url,
            options={
                "verify_exp": True,
                "verify_aud": False,
                "verify_iss": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(status_code=401, detail="Invalid token issuer") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("jwt_validation_failed", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    # Verify authorized party (azp) matches expected client — Keycloak always
    # sets azp even when aud is absent (default for public clients).
    azp = claims.get("azp")
    if azp and azp != settings.keycloak_client_id:
        raise HTTPException(status_code=401, detail="Invalid token client")

    return claims


def clear_jwks_cache() -> None:
    """Clear the JWKS cache (useful for testing)."""
    global _jwks_cache, _jwks_cache_time
    _jwks_cache = {}
    _jwks_cache_time = 0.0
