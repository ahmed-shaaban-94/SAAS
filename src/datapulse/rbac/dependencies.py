"""FastAPI dependencies for RBAC — role & permission guards, access context."""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.config import get_settings
from datapulse.core.db import get_session_factory
from datapulse.rbac.models import AccessContext, RoleKey
from datapulse.rbac.repository import RBACRepository
from datapulse.rbac.service import RBACService

logger = structlog.get_logger()


def _get_rbac_session(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> Session:
    """Create a raw (non-RLS) session for RBAC lookups.

    RBAC resolution happens before RLS scoping — we need to read
    tenant_members to determine the user's role, then use that role
    to decide what data to show.
    """
    session = get_session_factory()()
    tenant_id = user.get("tenant_id", "1")
    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    session.execute(text("SET LOCAL statement_timeout = '10s'"))
    return session


def _build_rbac_service(session: Session) -> RBACService:
    settings = get_settings()
    repo = RBACRepository(session)
    return RBACService(
        repo,
        owner_emails=settings.owner_emails,
        admin_emails=settings.admin_emails,
    )


def get_rbac_service(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> RBACService:
    session = _get_rbac_session(user)
    return _build_rbac_service(session)


def get_access_context(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> AccessContext:
    """Resolve the full access context for the current user.

    This dependency:
    1. Ensures the user has a tenant_members record (auto-registers on first login)
    2. Loads their role, permissions, and sector access
    3. Returns an AccessContext used by routes and sector filters
    """
    session = _get_rbac_session(user)
    try:
        service = _build_rbac_service(session)

        tenant_id = int(user.get("tenant_id", "1"))
        user_id = user.get("sub", "")
        email = user.get("email", "")
        name = user.get("preferred_username", "") or email.split("@")[0]

        # Auto-register if first login
        service.ensure_member_exists(tenant_id, user_id, email, name)
        session.commit()

        # Resolve full access context
        ctx = service.resolve_access(tenant_id, user_id)
        return ctx
    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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
