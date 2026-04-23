"""Tests for RBAC FastAPI dependencies — require_role, require_permission."""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from datapulse.core.auth import API_KEY_USER_ID
from datapulse.rbac.dependencies import (
    _API_KEY_SYNTHETIC_MEMBER_ID,
    _synthesize_api_key_context,
    get_access_context,
    require_permission,
    require_role,
)
from datapulse.rbac.models import AccessContext


def _ctx(role_key="viewer", permissions=None, **kw):
    return AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="u1",
        role_key=role_key,
        permissions=set(permissions or []),
        sector_ids=[],
        site_codes=[],
        is_admin=role_key in ("owner", "admin"),
        **kw,
    )


class TestRequireRole:
    def test_allowed_role(self):
        checker = require_role("owner", "admin")
        ctx = _ctx("admin")
        result = checker(ctx)
        assert result.role_key == "admin"

    def test_denied_role(self):
        checker = require_role("owner", "admin")
        ctx = _ctx("viewer")
        with pytest.raises(HTTPException) as exc_info:
            checker(ctx)
        assert exc_info.value.status_code == 403
        assert "viewer" in str(exc_info.value.detail)

    def test_single_role(self):
        checker = require_role("owner")
        ctx = _ctx("owner")
        result = checker(ctx)
        assert result.role_key == "owner"


class TestRequirePermission:
    def test_has_permission(self):
        checker = require_permission("analytics:view")
        ctx = _ctx(permissions=["analytics:view", "reports:view"])
        result = checker(ctx)
        assert "analytics:view" in result.permissions

    def test_missing_permission(self):
        checker = require_permission("pipeline:run")
        ctx = _ctx(permissions=["analytics:view"])
        with pytest.raises(HTTPException) as exc_info:
            checker(ctx)
        assert exc_info.value.status_code == 403
        assert "pipeline:run" in str(exc_info.value.detail)

    def test_multiple_permissions_all_required(self):
        checker = require_permission("analytics:view", "reports:create")
        ctx = _ctx(permissions=["analytics:view"])
        with pytest.raises(HTTPException) as exc_info:
            checker(ctx)
        assert "reports:create" in str(exc_info.value.detail)

    def test_multiple_permissions_all_present(self):
        checker = require_permission("analytics:view", "reports:create")
        ctx = _ctx(permissions=["analytics:view", "reports:create", "other"])
        result = checker(ctx)
        assert "analytics:view" in result.permissions


class TestSynthesizeApiKeyContext:
    def test_api_key_ctx_is_admin_with_admin_permissions(self):
        session = MagicMock()
        with patch("datapulse.rbac.dependencies.RBACRepository") as repo_cls:
            repo_cls.return_value.get_role_permissions.return_value = [
                "analytics:view",
                "reports:view",
                "members:manage",
            ]
            ctx = _synthesize_api_key_context(42, session)

        assert ctx.member_id == _API_KEY_SYNTHETIC_MEMBER_ID
        assert ctx.tenant_id == 42
        assert ctx.user_id == API_KEY_USER_ID
        assert ctx.role_key == "admin"
        assert ctx.is_admin is True
        assert "reports:view" in ctx.permissions
        assert ctx.sector_ids == []
        assert ctx.site_codes == []


class TestGetAccessContextApiKeyBypass:
    """Regression: /api/v1/reports via X-API-Key must not touch tenant_members.

    Previously, API-key callers (sub='api-key-user', email='') were auto-
    registered and collided on the (tenant_id, email) unique index as soon
    as a second emailless row existed.
    """

    def test_api_key_user_bypasses_auto_register(self):
        user = {
            "sub": API_KEY_USER_ID,
            "email": "",
            "preferred_username": "api-key",
            "tenant_id": "1",
            "roles": ["api-reader"],
            "raw_claims": {},
        }
        fake_session = MagicMock()

        with (
            patch(
                "datapulse.rbac.dependencies._get_rbac_session",
                return_value=nullcontext(fake_session),
            ),
            patch("datapulse.rbac.dependencies.RBACRepository") as repo_cls,
            patch("datapulse.rbac.dependencies._build_rbac_service") as build_service,
        ):
            repo_cls.return_value.get_role_permissions.return_value = ["reports:view"]
            ctx = get_access_context(user)

        # No service construction, no ensure_member_exists, no INSERT path.
        build_service.assert_not_called()
        fake_session.commit.assert_not_called()

        assert ctx.user_id == API_KEY_USER_ID
        assert ctx.tenant_id == 1
        assert ctx.role_key == "admin"
        assert ctx.is_admin is True
        assert "reports:view" in ctx.permissions

    def test_api_key_session_closed_on_error(self):
        user = {
            "sub": API_KEY_USER_ID,
            "email": "",
            "preferred_username": "api-key",
            "tenant_id": "1",
            "roles": [],
            "raw_claims": {},
        }
        fake_session = MagicMock()

        with (
            patch(
                "datapulse.rbac.dependencies._get_rbac_session",
                return_value=nullcontext(fake_session),
            ),
            patch("datapulse.rbac.dependencies.RBACRepository") as repo_cls,
        ):
            repo_cls.return_value.get_role_permissions.side_effect = RuntimeError("boom")
            with pytest.raises(RuntimeError, match="boom"):
                get_access_context(user)
