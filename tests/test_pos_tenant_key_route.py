"""GET /pos/tenant-key route tests — minimal app + mocked session."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service, get_tenant_plan_limits, get_tenant_session
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.exceptions import PosError
from datapulse.pos.tenant_keys import TenantKey
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit


_MOCK_USER: dict[str, Any] = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


def _make_app(fake_keys: list[TenantKey]) -> FastAPI:
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()

    @app.exception_handler(PosError)
    async def _pos_err(_req: Request, exc: PosError):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.include_router(pos_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()
    app.dependency_overrides[get_pos_service] = lambda: MagicMock()
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: AccessContext(
        member_id=1, tenant_id=1, user_id="test-user", role_key="admin",
        permissions=set(), is_admin=True,
    )

    # Patch list_public_keys to return our fake keys regardless of session
    import datapulse.api.routes.pos as pos_routes
    pos_routes.list_public_keys = lambda _sess, _tid: fake_keys  # type: ignore[assignment]

    return app


def test_tenant_key_endpoint_returns_encoded_public_keys() -> None:
    now = datetime.now(timezone.utc)
    keys = [
        TenantKey("k1", 1, b"p" * 32, b"\x01" * 32, now, now + timedelta(days=1)),
        TenantKey("k2", 1, b"q" * 32, b"\x02" * 32, now, now + timedelta(days=2)),
    ]
    client = TestClient(_make_app(keys))
    r = client.get("/api/v1/pos/tenant-key", headers={"X-API-Key": "test-api-key"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["keys"]) == 2
    ids = [k["key_id"] for k in body["keys"]]
    assert ids == ["k1", "k2"]
    for k in body["keys"]:
        # base64-url without padding, 43 chars for a 32-byte key
        assert len(k["public_key"]) == 43


def test_tenant_key_endpoint_returns_empty_list_when_no_keys() -> None:
    client = TestClient(_make_app([]))
    r = client.get("/api/v1/pos/tenant-key", headers={"X-API-Key": "test-api-key"})
    assert r.status_code == 200
    assert r.json() == {"keys": []}
