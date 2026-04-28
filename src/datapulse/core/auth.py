"""Authentication and authorization primitives — framework-agnostic core.

Canonical home for:

- :class:`UserClaims` — typed JWT claim structure.
- :func:`get_current_user` — JWT Bearer with API-key fallback (FastAPI dep).
- :func:`get_optional_user` / :func:`get_optional_user_for_health` — optional variants.
- :func:`require_api_key` — lightweight API-key guard (backwards compat).
- :func:`require_pipeline_token` — webhook token guard for pipeline endpoints.
- :func:`get_tenant_session` — RLS-scoped DB session dependency.

Lives in ``core/`` so business modules can depend on it without importing
from ``api/`` (issue #541). ``api/auth.py`` and ``api/deps.py`` keep thin
re-export shims for backwards compatibility with existing imports and
test ``dependency_overrides`` setups that reference the old paths.
"""

from __future__ import annotations

import re
import time
from collections.abc import Generator
from functools import lru_cache
from typing import Annotated, Any, TypedDict

import structlog
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from datapulse.cache import current_tenant_id
from datapulse.config import Settings, get_settings
from datapulse.core.config import is_non_dev_env
from datapulse.core.db import get_readonly_session_factory, get_session_factory
from datapulse.core.jwt import verify_jwt
from datapulse.core.security import compare_secrets

_auth_logger = structlog.get_logger()
_db_logger = structlog.get_logger()
_TENANT_ID_RE = re.compile(r"^\d{1,10}$")

# Sentinel user_id used when a caller authenticates with a shared X-API-Key.
# API-key callers are service credentials, not tenant users — RBAC auto-
# registration is bypassed for this sentinel (see rbac/dependencies.py).
API_KEY_USER_ID = "api-key-user"


class UserClaims(TypedDict):
    """Typed structure for authenticated user JWT claims."""

    sub: str
    email: str
    preferred_username: str
    tenant_id: str
    locale: str  # BCP-47 tag; default 'en-US' (#604)
    roles: list[str]
    raw_claims: dict[str, Any]


# Header schemes (auto_error=False so we control the error message)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_pipeline_token_header = APIKeyHeader(name="X-Pipeline-Token", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=64)
def _log_dev_tenant_fallback_once(minute_bucket: int) -> None:
    """Warn once per minute when JWT lacks a tenant claim in dev mode.

    ``lru_cache`` keyed on the monotonic-minute bucket means only the first
    call inside a given minute actually logs; subsequent calls hit the cache
    and are silent. ``maxsize=64`` keeps ~1h of bucket history before evicting
    the oldest, which is far larger than any realistic concurrent-minute
    window and avoids unbounded cache growth.
    """
    _auth_logger.warning(
        "jwt_missing_tenant_id_dev_fallback",
        detail=(
            "JWT has no tenant claim; falling back to default_tenant_id in "
            "dev mode. Add a 'tenant_id' claim to the Clerk JWT template before "
            "deploying to staging/production, or requests will be 401-rejected."
        ),
    )


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

    Refuses to run when ``settings.pipeline_webhook_secret`` is empty — there
    is no kill-switch. The legacy ``PIPELINE_AUTH_DISABLED`` env var was
    removed in issue #539 because a single misconfigured variable disabled
    webhook auth entirely. For local development, set any non-empty dev
    token (see docs/RUNBOOK.md §7).
    """
    if not settings.pipeline_webhook_secret:
        _auth_logger.error(
            "pipeline_auth_unconfigured",
            detail="PIPELINE_WEBHOOK_SECRET is empty",
        )
        raise HTTPException(status_code=503, detail="Pipeline auth not configured")
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
    """
    # 1. Try JWT Bearer token first
    if credentials is not None:
        claims = verify_jwt(credentials.credentials, settings)
        tenant_id = (
            claims.get("https://datapulse.tech/tenant_id")
            or claims.get("tenant_id")
            or claims.get("tid")
        )
        if not tenant_id:
            # Production: no fallback ever — a misconfigured Clerk JWT template must
            # not silently route users to ``default_tenant_id`` (#546).
            if is_non_dev_env(settings.app_env, settings.sentry_environment):
                _auth_logger.warning(
                    "jwt_missing_tenant_id_production_rejected",
                    sub=claims.get("sub"),
                    app_env=settings.app_env,
                    sentry_environment=settings.sentry_environment,
                )
                raise HTTPException(
                    status_code=401,
                    detail="JWT missing tenant context",
                )
            # Defense in depth: a cleared default in dev also rejects.
            if not settings.default_tenant_id:
                _auth_logger.warning(
                    "jwt_missing_tenant_id_rejected",
                    sub=claims.get("sub"),
                )
                raise HTTPException(
                    status_code=401,
                    detail="JWT missing tenant context",
                )
            # Dev: rate-limited warning so the log isn't flooded under load.
            tenant_id = settings.default_tenant_id
            _log_dev_tenant_fallback_once(int(time.monotonic() // 60))
        tenant_id_str = str(tenant_id)
        if tenant_id_str and not _TENANT_ID_RE.match(tenant_id_str):
            _auth_logger.warning("invalid_tenant_id", raw=tenant_id)
            raise HTTPException(status_code=401, detail="Invalid tenant context")
        roles = (
            claims.get("https://datapulse.tech/roles")
            or claims.get("permissions")
            or claims.get("roles")
            or []
        )
        locale = str(claims.get("locale") or "en-US")
        return {
            "sub": claims.get("sub", ""),
            "email": claims.get("email", ""),
            "preferred_username": claims.get("preferred_username", ""),
            "tenant_id": tenant_id_str,
            "locale": locale,
            "roles": roles,
            "raw_claims": claims,
        }

    # 2. Fallback to API key
    if api_key:
        if settings.api_key and compare_secrets(api_key, settings.api_key):
            return {
                "sub": API_KEY_USER_ID,
                "email": "",
                "preferred_username": "api-key",
                "tenant_id": settings.default_tenant_id,
                "locale": "en-US",
                "roles": list(settings.api_key_roles),
                "raw_claims": {},
            }
        raise HTTPException(status_code=401, detail="Authentication failed")

    # 3. Dev mode — neither API key nor the active IdP is configured.
    # SECURITY: defense-in-depth gate. Refuse the fallback whenever *either*
    # app_env or sentry_environment indicates a non-dev deployment, so a single
    # misconfigured env var cannot leak admin-adjacent claims (issue #537).
    # ``_jwt_provider_configured`` confirms Clerk is configured.
    if not settings.api_key and not settings._jwt_provider_configured:
        if is_non_dev_env(settings.app_env, settings.sentry_environment):
            _auth_logger.error(
                "auth_not_configured_in_production",
                app_env=settings.app_env,
                sentry_environment=settings.sentry_environment,
                detail="API_KEY and CLERK_JWT_ISSUER are both empty in a non-dev "
                "environment — refusing to return dev fallback claims",
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
            "locale": "en-US",
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

    Only silences 401/403 (unauthenticated / forbidden). Other HTTP errors
    (e.g. 503 Clerk outage) are re-raised so callers receive a truthful
    error instead of silent anonymous access.
    """
    try:
        return get_current_user(credentials, api_key, settings)
    except HTTPException as exc:
        if exc.status_code not in (401, 403):
            raise
        return None


def get_optional_user_for_health(
    credentials: HTTPAuthorizationCredentials | None = Security(  # noqa: B008
        _bearer_scheme
    ),
    api_key: str | None = Security(_api_key_header),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserClaims | None:
    """Optional-user resolver for ``/health`` only — silences ALL exceptions.

    The regular :func:`get_optional_user` re-raises Clerk outages (503) so
    normal routes surface a truthful error. For ``/health`` we want the
    opposite: DB / Redis health must be reportable even when Clerk is down.
    """
    try:
        return get_current_user(credentials, api_key, settings)
    except Exception:
        return None


def get_tenant_session(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> Generator[Session, None, None]:
    """Create a DB session scoped to the authenticated user's tenant.

    Extracts tenant_id from JWT claims and sets it via ``SET LOCAL`` so
    that PostgreSQL RLS policies filter data automatically.

    Audit M1 (2026-04-26): the previous ``or "1"`` fallback turned a
    missing claim into a silent cross-tenant exposure on tenant ``1``.
    ``get_current_user`` is the canonical source of the claim, but this
    is the last gate before SQL runs — fail loudly if anything bypasses
    it (test override, future refactor, direct callers).
    """
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id claim missing")
    current_tenant_id.set(str(tenant_id))
    structlog.contextvars.bind_contextvars(tenant_id=str(tenant_id))
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        yield session
        session.commit()
    except SQLAlchemyError:
        _db_logger.exception("db_session_error", session_type="tenant", tenant_id=str(tenant_id))
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")


def get_tenant_session_readonly(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> Generator[Session, None, None]:
    """Tenant session that prefers the read replica; falls back to primary on error.

    Use for idempotent GET endpoints where a < 5 s replication lag is
    acceptable (dashboards, reports, analytics). Never use for POS
    checkout or any read-after-write that must see its own writes —
    those require :func:`get_tenant_session` on the primary (#608).

    Fallback cases (all transparent to the caller):
      - ``database_replica_url`` unset → get_readonly_engine returns primary.
      - Replica connection fails at session open → retry on primary.
    """
    from datapulse.metrics import db_replica_fallbacks, db_replica_hits

    # Audit M1 (2026-04-26): mirror ``get_tenant_session`` — silent fallback
    # to tenant ``"1"`` on read endpoints would be the same exposure.
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id claim missing")
    current_tenant_id.set(str(tenant_id))
    structlog.contextvars.bind_contextvars(tenant_id=str(tenant_id))

    settings = get_settings()
    replica_configured = bool(settings.database_replica_url)

    session: Session | None = None
    used_replica = False
    if replica_configured:
        try:
            session = get_readonly_session_factory()()
            used_replica = True
            db_replica_hits.inc()
        except SQLAlchemyError as exc:
            _db_logger.warning(
                "replica_unavailable_fallback_to_primary",
                error=str(exc),
                tenant_id=str(tenant_id),
            )
            db_replica_fallbacks.labels(reason="error").inc()
            session = None
    if session is None:
        if not replica_configured:
            db_replica_fallbacks.labels(reason="unconfigured").inc()
        session = get_session_factory()()

    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        # Replica sessions are read-only by intent — make it explicit so a
        # stray INSERT/UPDATE fails loudly instead of silently landing on
        # the primary if a dev accidentally binds write code to this dep.
        if used_replica:
            session.execute(text("SET LOCAL default_transaction_read_only = on"))
        yield session
        session.commit()
    except SQLAlchemyError:
        _db_logger.exception(
            "db_session_error",
            session_type="tenant_readonly",
            tenant_id=str(tenant_id),
            used_replica=used_replica,
        )
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")


# Type aliases for FastAPI dependency injection
SessionDep = Annotated[Session, Depends(get_tenant_session)]
SessionDepReadOnly = Annotated[Session, Depends(get_tenant_session_readonly)]
CurrentUser = Annotated[UserClaims, Depends(get_current_user)]
