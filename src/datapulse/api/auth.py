"""Authentication and authorization for the FastAPI API.

Provides:
- ``get_current_user``: JWT Bearer token auth (primary) with API-key fallback.
- ``get_optional_user``: Same as above but returns None instead of raising.
- ``require_api_key``: Lightweight API-key guard (backwards compatibility).
- ``require_pipeline_token``: Webhook token guard for pipeline endpoints.

When the corresponding config value is empty, the guard is skipped (dev mode).
"""

from __future__ import annotations

import os
import re
from typing import Any, TypedDict

import structlog
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from datapulse.api.jwt import verify_jwt
from datapulse.config import Settings, get_settings
from datapulse.core.security import compare_secrets

_auth_logger = structlog.get_logger()
_TENANT_ID_RE = re.compile(r"^\d{1,10}$")


class UserClaims(TypedDict):
    """Typed structure for authenticated user JWT claims."""

    sub: str
    email: str
    preferred_username: str
    tenant_id: str
    roles: list[str]
    raw_claims: dict[str, Any]


# Header schemes (auto_error=False so we control the error message)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_pipeline_token_header = APIKeyHeader(name="X-Pipeline-Token", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


def require_api_key(
    api_key: str | None = Security(_api_key_header),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> None:
    """Verify the X-API-Key header matches the configured api_key.

    Skips validation when ``settings.api_key`` is empty (dev / local mode).
    """
    if not settings.api_key:
        return  # dev mode — no auth required
    if not api_key or not compare_secrets(api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Authentication failed")


def require_pipeline_token(
    token: str | None = Security(_pipeline_token_header),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> None:
    """Verify the X-Pipeline-Token header for pipeline execution endpoints.

    Skips validation when ``settings.pipeline_webhook_secret`` is empty.
    """
    if not settings.pipeline_webhook_secret:
        if os.getenv("PIPELINE_AUTH_DISABLED", "").lower() != "true":
            _auth_logger.error(
                "pipeline_auth_unconfigured",
                detail="PIPELINE_WEBHOOK_SECRET is empty and PIPELINE_AUTH_DISABLED is not set",
            )
            raise HTTPException(status_code=503, detail="Pipeline auth not configured")
        return  # explicitly opted-in to no auth
    if not token or not compare_secrets(token, settings.pipeline_webhook_secret):
        raise HTTPException(status_code=403, detail="Authentication failed")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(  # noqa: B008
        _bearer_scheme
    ),
    api_key: str | None = Security(_api_key_header),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserClaims:
    """Authenticate the current user via JWT Bearer token or API key fallback.

    Priority:
    1. Bearer token present -> verify JWT, return claims
    2. No Bearer token but X-API-Key present -> verify API key, return stub claims
    3. Both auth mechanisms are unconfigured (dev mode) -> return dev claims

    Returns a dict of user claims with at least:
    - ``sub``: user subject identifier
    - ``tenant_id``: tenant identifier for RLS
    - ``roles``: list of realm roles
    """
    # 1. Try JWT Bearer token first
    if credentials is not None:
        claims = verify_jwt(credentials.credentials, settings)
        # Extract tenant_id — check namespaced Auth0 claim, then standard claims,
        # then fall back to default_tenant_id for single-tenant deployments.
        tenant_id = (
            claims.get("https://datapulse.tech/tenant_id")
            or claims.get("tenant_id")
            or claims.get("tid")
        )
        if not tenant_id:
            if not settings.default_tenant_id:
                _auth_logger.warning(
                    "jwt_missing_tenant_id_rejected",
                    sub=claims.get("sub"),
                )
                raise HTTPException(
                    status_code=401,
                    detail="JWT missing tenant context",
                )
            tenant_id = settings.default_tenant_id
            _auth_logger.warning(
                "jwt_missing_tenant_id",
                sub=claims.get("sub"),
                detail="Falling back to default_tenant_id; add tenant_id claim to Auth0 Action",
            )
        tenant_id_str = str(tenant_id)
        if tenant_id_str and not _TENANT_ID_RE.match(tenant_id_str):
            _auth_logger.warning("invalid_tenant_id", raw=tenant_id)
            raise HTTPException(status_code=401, detail="Invalid tenant context")
        # Extract roles — Auth0 uses a namespaced custom claim or permissions
        # Auth0 custom rule/action can set roles at a namespace like
        # "https://datapulse.tech/roles" or in the "permissions" claim.
        roles = (
            claims.get("https://datapulse.tech/roles")
            or claims.get("permissions")
            or claims.get("roles")
            or []
        )
        return {
            "sub": claims.get("sub", ""),
            "email": claims.get("email", ""),
            "preferred_username": claims.get("preferred_username", ""),
            "tenant_id": tenant_id_str,
            "roles": roles,
            "raw_claims": claims,
        }

    # 2. Fallback to API key
    if api_key:
        if settings.api_key and compare_secrets(api_key, settings.api_key):
            return {
                "sub": "api-key-user",
                "email": "",
                "preferred_username": "api-key",
                "tenant_id": settings.default_tenant_id,
                "roles": list(settings.api_key_roles),
                "raw_claims": {},
            }
        raise HTTPException(status_code=401, detail="Authentication failed")

    # 3. Dev mode — both auth mechanisms unconfigured
    if not settings.api_key and not settings.auth0_domain:
        env = settings.sentry_environment
        if env not in ("development", "test"):
            _auth_logger.error(
                "auth_not_configured_in_production",
                environment=env,
                detail="API_KEY and AUTH0_DOMAIN are both empty in non-dev environment "
                "— refusing to return dev fallback with admin roles",
            )
            raise HTTPException(
                status_code=503,
                detail="Authentication not configured. Contact the administrator.",
            )
        return {
            "sub": "dev-user",
            "email": "dev@datapulse.local",
            "preferred_username": "dev",
            "tenant_id": settings.default_tenant_id,
            "roles": ["viewer"],
            "raw_claims": {},
        }

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
    )


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(  # noqa: B008
        _bearer_scheme
    ),
    api_key: str | None = Security(_api_key_header),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserClaims | None:
    """Same as get_current_user but returns None on missing/invalid auth.

    Only silences 401/403 (unauthenticated / forbidden).
    Other HTTP errors (e.g. 503 Auth0 outage) are re-raised so callers
    receive a truthful error instead of silent anonymous access.
    """
    try:
        return get_current_user(credentials, api_key, settings)
    except HTTPException as exc:
        if exc.status_code not in (401, 403):
            raise
        return None
