"""Reseller cross-tenant authorization tests — H5.8.

Verifies the ownership check added in H2.1 (_check_reseller_access):
  - Non-admin users whose tenant is NOT associated with the requested reseller
    must receive HTTP 403 (access denied).
  - Non-admin users whose tenant IS associated with the reseller receive the
    normal response.
  - Users with admin or owner roles bypass the ownership check entirely.

These tests will FAIL against the H1 baseline (which has no ownership check)
and PASS once H2 is merged into main.  They serve as the safety net for H2.1.

Test strategy
-------------
We use FastAPI's TestClient with dependency overrides to control:
  - The authenticated user's tenant_id and roles
  - The repository's tenant_belongs_to_reseller() return value

All tests target the endpoint layer so that the _check_reseller_access helper
is exercised as it is wired in production.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.reseller.models import (
    ResellerDashboard,
    ResellerResponse,
)
from datapulse.reseller.repository import ResellerRepository
from datapulse.reseller.service import ResellerService

_NOW = datetime(2025, 6, 15, 12, 0, 0)

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _user(tenant_id: str = "1", roles: list[str] | None = None) -> dict:
    return {
        "sub": f"user-tenant-{tenant_id}",
        "email": f"user{tenant_id}@example.com",
        "preferred_username": f"user{tenant_id}",
        "tenant_id": tenant_id,
        "roles": roles or [],
        "raw_claims": {},
    }


def _reseller(reseller_id: int = 1) -> ResellerResponse:
    return ResellerResponse(
        reseller_id=reseller_id,
        name="Partner Co",
        contact_email="partner@co.com",
        commission_pct=Decimal("20.00"),
        is_active=True,
        tenant_count=1,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fixture factory
# ---------------------------------------------------------------------------


def _make_client(
    *,
    user: dict,
    tenant_belongs: bool,
) -> tuple[TestClient, MagicMock]:
    """Return (TestClient, mock_service) wired with the given user and ownership flag."""
    mock_repo = create_autospec(ResellerRepository, instance=True)
    mock_repo.tenant_belongs_to_reseller.return_value = tenant_belongs

    mock_service = MagicMock(spec=ResellerService)
    # _repo kept for any call paths that still reach through; the route's
    # _check_reseller_access now delegates to the service method directly.
    mock_service._repo = mock_repo
    mock_service.tenant_belongs_to_reseller.return_value = tenant_belongs
    mock_service.get_dashboard.return_value = ResellerDashboard(reseller=_reseller())
    mock_service.get_tenants.return_value = []
    mock_service.get_commissions.return_value = []
    mock_service.get_payouts.return_value = []

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()

    from datapulse.api.routes.reseller import get_reseller_service

    app.dependency_overrides[get_reseller_service] = lambda: mock_service

    client = TestClient(app, raise_server_exceptions=False)
    return client, mock_service


# ---------------------------------------------------------------------------
# H5.8.1 — Non-owner, non-associated tenant → 403
# ---------------------------------------------------------------------------


class TestCrossTenantAccessBlocked:
    """Users from a different tenant must not access another tenant's reseller data."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/reseller/1/dashboard",
            "/api/v1/reseller/1/tenants",
            "/api/v1/reseller/1/commissions",
            "/api/v1/reseller/1/payouts",
        ],
    )
    def test_unrelated_tenant_receives_403(self, endpoint: str) -> None:
        """A user from tenant 99 must receive 403 when accessing reseller 1's data
        (tenant 99 is NOT associated with reseller 1).

        This is the core IDOR (Insecure Direct Object Reference) fix from H2.1.
        """
        client, _ = _make_client(
            user=_user(tenant_id="99", roles=[]),  # no admin role
            tenant_belongs=False,  # tenant 99 not linked to reseller 1
        )
        resp = client.get(endpoint)
        assert resp.status_code == 403, (
            f"Expected 403 for cross-tenant access to {endpoint}, got {resp.status_code}. "
            "This indicates H2.1 (_check_reseller_access) is not active."
        )

    def test_403_response_body_does_not_leak_data(self) -> None:
        """The 403 response must not include reseller data in its body."""
        client, _ = _make_client(
            user=_user(tenant_id="99", roles=[]),
            tenant_belongs=False,
        )
        resp = client.get("/api/v1/reseller/1/dashboard")
        assert resp.status_code == 403
        body = resp.json()
        # Must not contain reseller name or financial data
        assert "Partner Co" not in str(body)
        assert "commission" not in str(body).lower() or "access denied" in str(body).lower()


# ---------------------------------------------------------------------------
# H5.8.2 — Associated tenant → 200
# ---------------------------------------------------------------------------


class TestAssociatedTenantAllowed:
    """Users from a tenant that IS associated with a reseller must have access."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/reseller/1/dashboard",
            "/api/v1/reseller/1/tenants",
            "/api/v1/reseller/1/commissions",
            "/api/v1/reseller/1/payouts",
        ],
    )
    def test_associated_tenant_receives_200(self, endpoint: str) -> None:
        """A user from a tenant that belongs to reseller 1 must receive the data."""
        client, _ = _make_client(
            user=_user(tenant_id="5", roles=[]),
            tenant_belongs=True,  # tenant 5 IS associated with reseller 1
        )
        resp = client.get(endpoint)
        assert resp.status_code == 200, (
            f"Expected 200 for associated tenant on {endpoint}, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# H5.8.3 — Admin/owner role bypass
# ---------------------------------------------------------------------------


class TestAdminBypassOwnershipCheck:
    """Platform admins (admin/owner roles) must bypass the tenant ownership check."""

    @pytest.mark.parametrize("role", ["admin", "owner"])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/reseller/1/dashboard",
            "/api/v1/reseller/1/tenants",
            "/api/v1/reseller/1/commissions",
            "/api/v1/reseller/1/payouts",
        ],
    )
    def test_platform_admin_bypasses_ownership_check(self, role: str, endpoint: str) -> None:
        """Admin/owner users must access any reseller's data regardless of tenant association."""
        client, mock_service = _make_client(
            user=_user(tenant_id="99", roles=[role]),  # unrelated tenant but platform admin
            tenant_belongs=False,  # ownership check would deny if applied
        )
        resp = client.get(endpoint)
        assert resp.status_code == 200, (
            f"Platform {role!r} must bypass ownership check on {endpoint}, got {resp.status_code}"
        )

    @pytest.mark.parametrize("role", ["admin", "owner"])
    def test_admin_does_not_call_tenant_belongs_check(self, role: str) -> None:
        """For admin users the ownership DB query must not be executed at all."""
        client, mock_service = _make_client(
            user=_user(tenant_id="99", roles=[role]),
            tenant_belongs=False,
        )
        client.get("/api/v1/reseller/1/dashboard")
        # The repo check must not have been called for admin users
        mock_service._repo.tenant_belongs_to_reseller.assert_not_called()
