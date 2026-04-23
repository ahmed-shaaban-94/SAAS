"""JWT verification using Clerk's JWKS endpoint.

Reads the JWKS URL, issuer, audience, and expected ``azp`` from
:class:`Settings`' ``active_*`` properties. Keys are cached per URL with a TTL.
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

# Module-level JWKS cache — keyed by URL so switching AUTH_PROVIDER at
# runtime (or in tests) never returns the previous provider's keys.
_jwks_cache: dict[str, tuple[dict[str, Any], float]] = {}
_JWKS_CACHE_TTL: int = 3600  # 1 hour (keys rarely rotate; miss triggers forced refresh)


def _fetch_jwks(settings: Settings) -> dict[str, Any]:
    """Fetch JWKS from the active IdP, with in-memory TTL cache and retry backoff.

    Attempts up to 3 times (delays: 0.5s, 1s, 2s) on network/timeout errors.
    HTTP 4xx responses are not retried — they indicate a configuration error.
    Returns stale cache as a last resort before raising 503.
    """
    jwks_url = settings.active_jwks_url
    if not jwks_url:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        )

    now = time.monotonic()
    cached = _jwks_cache.get(jwks_url)
    if cached is not None and (now - cached[1]) < _JWKS_CACHE_TTL:
        return cached[0]

    last_exc: Exception | None = None

    for attempt, delay in enumerate((*_JWKS_RETRY_DELAYS, None), start=1):  # type: ignore[arg-type]
        try:
            resp = httpx.get(jwks_url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            _jwks_cache[jwks_url] = (data, time.monotonic())
            logger.info("jwks_fetched", url=jwks_url, attempt=attempt)
            return data
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
    # Return stale cache for *this URL* if available (better than hard failure)
    stale = _jwks_cache.get(jwks_url)
    if stale is not None:
        logger.warning("jwks_using_stale_cache", url=jwks_url)
        return stale[0]
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

    # Key not found — maybe keys rotated; expire this URL's cache and retry once
    _jwks_cache.pop(settings.active_jwks_url, None)
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
    """Decode and verify a JWT using the active IdP's JWKS keys.

    Returns the decoded claims dict on success.
    Raises HTTPException(401) on invalid/expired tokens.
    Raises HTTPException(503) if the IdP's JWKS endpoint is unreachable.
    """
    if settings is None:
        settings = get_settings()

    signing_key = _get_signing_key(token, settings)
    audience = settings.active_audience

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.active_issuer_url,
            audience=audience or None,
            options={
                "verify_exp": True,
                "verify_aud": bool(audience),
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

    # Verify azp (authorized party) only when the active IdP supplies a
    # stable expected value. Auth0 puts the client_id there; Clerk puts the
    # Frontend API URL which is already covered by the issuer check, so we
    # deliberately skip azp for Clerk.
    expected_azp = settings.active_expected_azp
    if expected_azp:
        azp = claims.get("azp")
        if azp and azp != expected_azp:
            raise HTTPException(status_code=401, detail="Invalid token client")

    return claims


def clear_jwks_cache() -> None:
    """Clear the JWKS cache (useful for testing and provider swaps)."""
    _jwks_cache.clear()
