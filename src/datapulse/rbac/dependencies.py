"""FastAPI dependencies for RBAC — role & permission guards, access context."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import AbstractContextManager
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from datapulse.config import get_settings
from datapulse.core.auth import API_KEY_USER_ID, UserClaims, get_current_user
from datapulse.core.db import tenant_session_scope
from datapulse.rbac.models import AccessContext, RoleKey
from datapulse.rbac.repository import RBACRepository
from datapulse.rbac.service import RBACService

# Synthetic member_id for API-key callers. Never matches a real
# tenant_members.member_id (which is SERIAL, starts at 1).
_API_KEY_SYNTHETIC_MEMBER_ID = 0


def _synthesize_api_key_context(tenant_id: int, session: Session) -> AccessContext:
    """Build an AccessContext for API-key (service credential) callers.

    API-key callers are shared service credentials, not tenant users, and
    must not be auto-registered into ``tenant_members`` — that path would
    collide on the ``(tenant_id, email)`` unique index the moment any
    other API-key-user row already exists with an empty email.

    The synthesized context grants admin-level access: all permissions
    assigned to the ``admin`` role, no sector restriction. Endpoint-level
    gating still applies via ``require_auth_role`` / ``require_api_key``.
    """
    repo = RBACRepository(session)
    permissions = set(repo.get_role_permissions("admin"))
    return AccessContext(
        member_id=_API_KEY_SYNTHETIC_MEMBER_ID,
        tenant_id=tenant_id,
        user_id=API_KEY_USER_ID,
        role_key="admin",
        permissions=permissions,
        sector_ids=[],
        site_codes=[],
        is_admin=True,
    )


def _get_rbac_session(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> AbstractContextManager[Session]:
    """Create a raw (non-RLS) session for RBAC lookups.

    RBAC resolution happens before RLS scoping — we need to read
    tenant_members to determine the user's role, then use that role
    to decide what data to show.
    """
    tenant_id = user.get("tenant_id", "1")
    return tenant_session_scope(
        tenant_id,
        statement_timeout="10s",
        session_type="rbac",
    )


def _build_rbac_service(session: Session) -> RBACService:
    settings = get_settings()
    repo = RBACRepository(session)
    return RBACService(
        repo,
        owner_emails=settings.owner_emails,
        admin_emails=settings.admin_emails,
    )


def get_rbac_service(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> Generator[RBACService, None, None]:
    """Yield an RBACService and guarantee the underlying session is closed."""
    with _get_rbac_session(user) as session:
        yield _build_rbac_service(session)


def get_access_context(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> AccessContext:
    """Resolve the full access context for the current user.

    This dependency:
    1. Ensures the user has a tenant_members record (auto-registers on first login)
    2. Loads their role, permissions, and sector access
    3. Returns an AccessContext used by routes and sector filters
    """
    try:
        with _get_rbac_session(user) as session:
            tenant_id = int(user.get("tenant_id", "1"))
            user_id = user.get("sub", "")

            # API-key callers are service credentials — never tenant_members
            # rows. Short-circuit to a synthetic admin context so we don't
            # attempt to INSERT a duplicate row with empty email (issue:
            # tenant_members_tenant_id_email_key unique violation).
            if user_id == API_KEY_USER_ID:
                return _synthesize_api_key_context(tenant_id, session)

            service = _build_rbac_service(session)
            email = user.get("email", "")
            name = user.get("preferred_username", "") or email.split("@")[0]

            # Auto-register if first login
            service.ensure_member_exists(tenant_id, user_id, email, name)
            session.commit()

            # Resolve full access context
            ctx = service.resolve_access(tenant_id, user_id)
            return ctx
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# Type alias for convenience
AccessCtx = Annotated[AccessContext, Depends(get_access_context)]


def require_role(*allowed_roles: RoleKey):
    """Dependency factory: require the user to have one of the specified roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("owner", "admin"))])
    """

    def _check(ctx: AccessCtx) -> AccessContext:
        if ctx.role_key not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Role '{ctx.role_key}' is not authorized. Required: {', '.join(allowed_roles)}"
                ),
            )
        return ctx

    return _check


def require_permission(*required_perms: str):
    """Dependency factory: require the user to have all specified permissions.

    Usage:
        @router.post("/run", dependencies=[Depends(require_permission("pipeline:run"))])
    """

    def _check(ctx: AccessCtx) -> AccessContext:
        missing = set(required_perms) - ctx.permissions
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permissions: {', '.join(sorted(missing))}",
            )
        return ctx

    return _check
