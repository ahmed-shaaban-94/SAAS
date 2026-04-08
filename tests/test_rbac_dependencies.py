"""Tests for RBAC FastAPI dependencies — require_role, require_permission."""

import pytest
from fastapi import HTTPException

from datapulse.rbac.dependencies import require_permission, require_role
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
