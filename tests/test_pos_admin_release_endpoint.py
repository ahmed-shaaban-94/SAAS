"""Endpoint tests for ``POST /api/v1/pos/admin/desktop-releases``.

Covers:
* 201 happy path with body echo
* idempotent re-call returns the same release_id
* 403 when the caller lacks ``pos:update:manage``
* 422 on a blank version
* 402 when the caller's tenant is not on the platform/enterprise plan
  (verifies the inherited ``require_pos_plan`` from the parent router)
* leading ``v`` prefix is stripped before reaching the service
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_plan_limits, get_tenant_session
from datapulse.api.routes.pos import router as pos_router
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.models.admin_release import DesktopReleaseResponse
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit


_OWNER_USER: dict[str, Any] = {
    "sub": "owner-user-001",
    "email": "owner@test.local",
    "tenant_id": "1",
    "roles": ["owner"],
    "raw_claims": {},
}

_CASHIER_USER: dict[str, Any] = {
    "sub": "cashier-user-001",
    "email": "cashier@test.local",
    "tenant_id": "1",
    "roles": ["pos_cashier"],
    "raw_claims": {},
}


def _release_response(
    *,
    release_id: int = 7,
    version: str = "9.9.10",
    release_notes: str | None = None,
) -> DesktopReleaseResponse:
    return DesktopReleaseResponse(
        release_id=release_id,
        version=version,
        channel="stable",
        platform="win32",
        rollout_scope="all",
        active=True,
        release_notes=release_notes,
        min_app_version=None,
        min_schema_version=None,
        max_schema_version=None,
        created_at=datetime(2026, 4, 30, tzinfo=UTC),
        updated_at=datetime(2026, 4, 30, tzinfo=UTC),
    )


def _make_app(
    *,
    user: dict[str, Any] | None,
    permissions: set[str],
    plan: str = "platform",
    upsert_side_effect=None,
) -> tuple[FastAPI, MagicMock]:
    """Mount the POS router with billing/RBAC bypassed.

    Returns the app plus a MagicMock standing in for the upsert_release
    service so tests can assert call args / configure idempotent return.
    """
    app = FastAPI()

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_access_context] = lambda: AccessContext(
            member_id=1,
            tenant_id=int(user["tenant_id"]),
            user_id=user["sub"],
            role_key=user["roles"][0],
            permissions=permissions,
        )
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS[plan]
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()

    upsert_mock = MagicMock()
    if upsert_side_effect is not None:
        upsert_mock.side_effect = upsert_side_effect
    else:
        upsert_mock.return_value = _release_response()

    # Patch the symbol the route module imports (resolved at request time
    # because Python re-binds each call through the module dict). Using
    # monkeypatch.setattr would also work; doing it via a MagicMock on
    # the imported function keeps the test fully self-contained.
    import datapulse.api.routes._pos_admin_releases as _mod

    _mod.upsert_release = upsert_mock  # type: ignore[assignment]

    app.include_router(pos_router, prefix="/api/v1")
    return app, upsert_mock


def test_post_release_201_happy_path() -> None:
    app, upsert_mock = _make_app(user=_OWNER_USER, permissions={"pos:update:manage"})
    upsert_mock.return_value = _release_response(version="9.9.10")

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/pos/admin/desktop-releases",
            json={
                "version": "9.9.10",
                "channel": "stable",
                "platform": "win32",
                "rollout_scope": "all",
                "active": True,
                "release_notes": "endpoint test",
            },
        )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["version"] == "9.9.10"
    assert body["release_id"] == 7
    upsert_mock.assert_called_once()


def test_post_release_idempotent_returns_same_release_id() -> None:
    app, upsert_mock = _make_app(user=_OWNER_USER, permissions={"pos:update:manage"})
    upsert_mock.side_effect = [
        _release_response(release_id=11, version="9.9.11"),
        _release_response(release_id=11, version="9.9.11", release_notes="updated"),
    ]

    payload = {
        "version": "9.9.11",
        "channel": "stable",
        "platform": "win32",
        "rollout_scope": "all",
        "active": True,
    }
    with TestClient(app) as client:
        first = client.post("/api/v1/pos/admin/desktop-releases", json=payload).json()
        second = client.post(
            "/api/v1/pos/admin/desktop-releases",
            json={**payload, "release_notes": "updated"},
        ).json()

    assert first["release_id"] == second["release_id"] == 11
    assert second["release_notes"] == "updated"
    assert upsert_mock.call_count == 2


def test_post_release_403_without_pos_update_manage_permission() -> None:
    app, _ = _make_app(user=_CASHIER_USER, permissions={"pos:transaction:create"})

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/pos/admin/desktop-releases",
            json={
                "version": "9.9.12",
                "channel": "stable",
                "platform": "win32",
            },
        )
    assert res.status_code == 403
    assert "pos:update:manage" in res.json()["detail"]


def test_post_release_strips_v_prefix_before_calling_service() -> None:
    """The Pydantic model strips ``v`` from versions; verify the service
    sees the stripped form so the DB row's ``version`` column never carries
    the prefix."""
    app, upsert_mock = _make_app(user=_OWNER_USER, permissions={"pos:update:manage"})
    upsert_mock.return_value = _release_response(version="9.9.13")

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/pos/admin/desktop-releases",
            json={"version": "v9.9.13", "channel": "stable", "platform": "win32"},
        )

    assert res.status_code == 201
    payload_arg = upsert_mock.call_args.args[1]
    assert payload_arg.version == "9.9.13"


def test_post_release_422_on_blank_version() -> None:
    app, upsert_mock = _make_app(user=_OWNER_USER, permissions={"pos:update:manage"})

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/pos/admin/desktop-releases",
            json={"version": "", "channel": "stable", "platform": "win32"},
        )

    assert res.status_code == 422
    upsert_mock.assert_not_called()


def test_post_release_402_when_tenant_not_on_pos_plan() -> None:
    """Verifies the inherited ``require_pos_plan`` from pos.router."""
    app, upsert_mock = _make_app(
        user=_OWNER_USER, permissions={"pos:update:manage"}, plan="starter"
    )

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/pos/admin/desktop-releases",
            json={
                "version": "9.9.14",
                "channel": "stable",
                "platform": "win32",
                "rollout_scope": "all",
            },
        )

    assert res.status_code == 402
    upsert_mock.assert_not_called()
