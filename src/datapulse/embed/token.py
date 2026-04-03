"""Embed token generation and validation.

Generates short-lived JWT tokens scoped to a specific resource (e.g.
a model or query) and tenant.  Used for iframe embedding where the
host page cannot pass session cookies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from datapulse.config import get_settings
from datapulse.logging import get_logger

log = get_logger(__name__)

_ISSUER = "datapulse-embed"
_ALGORITHM = "HS256"


def _get_secret() -> str:
    """Return the signing secret for embed tokens.

    Priority: EMBED_SECRET > API_KEY > raise error (no insecure fallback).
    """
    settings = get_settings()
    if settings.embed_secret:
        return settings.embed_secret
    if settings.api_key:
        log.warning(
            "embed_using_api_key",
            detail="Using API_KEY as embed secret — set EMBED_SECRET for production",
        )
        return settings.api_key
    raise ValueError(
        "EMBED_SECRET or API_KEY must be configured for embed token signing"
    )


def create_embed_token(
    tenant_id: str,
    resource_type: str = "explore",
    resource_id: str = "",
    expires_hours: int = 8,
) -> str:
    """Create a signed embed token.

    Parameters
    ----------
    tenant_id:
        Tenant ID for RLS scoping.
    resource_type:
        Type of embedded resource (e.g. "explore", "dashboard").
    resource_id:
        Specific resource identifier (optional).
    expires_hours:
        Token lifetime in hours.

    Returns
    -------
    A signed JWT string.
    """
    now = datetime.now(UTC)
    payload = {
        "iss": _ISSUER,
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
        "tenant_id": tenant_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    token = jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)
    log.info(
        "embed_token_created",
        tenant_id=tenant_id,
        resource_type=resource_type,
        expires_hours=expires_hours,
    )
    return token


def validate_embed_token(token: str) -> dict:
    """Validate and decode an embed token.

    Returns
    -------
    The decoded payload dict.

    Raises
    ------
    jwt.InvalidTokenError:
        If the token is invalid, expired, or has wrong issuer.
    """
    payload = jwt.decode(
        token,
        _get_secret(),
        algorithms=[_ALGORITHM],
        issuer=_ISSUER,
    )
    return payload
