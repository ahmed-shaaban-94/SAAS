"""Device registration route tests — minimal-app + mocked service."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from typing import Any
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service, get_tenant_plan_limits, get_tenant_session
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.exceptions import PosError
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit

_MOCK_USER: dict[str, Any] = {
    "sub": "admin-1",
    "email": "admin@datapulse.local",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


def _fresh_public_key() -> str:
    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    return urlsafe_b64encode(pk).decode().rstrip("=")


def _make_app(register_stub) -> FastAPI:
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
        member_id=1,
        tenant_id=1,
        user_id="admin-1",
        role_key="admin",
        permissions={"pos:device:register"},
        is_admin=True,
    )

    import datapulse.api.routes.pos as pos_routes

    pos_routes.register_device = register_stub  # type: ignore[assignment]
    return app


def test_register_device_route_returns_device_id() -> None:
    seen: dict[str, Any] = {}

    def _register(
        session,
        *,
        tenant_id,
        terminal_id,
        public_key_b64,
        device_fingerprint,
        device_fingerprint_v2=None,
    ):
        seen["tenant_id"] = tenant_id
        seen["terminal_id"] = terminal_id
        seen["device_fingerprint_v2"] = device_fingerprint_v2
        return 99

    client = TestClient(_make_app(_register))
    r = client.post(
        "/api/v1/pos/terminals/register-device",
        json={
            "terminal_id": 11,
            "public_key": _fresh_public_key(),
            "device_fingerprint": "sha256:" + "a" * 64,
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["device_id"] == 99
    assert body["terminal_id"] == 11
    assert "registered_at" in body
    assert seen["terminal_id"] == 11
    assert seen["tenant_id"] == 1
    assert seen["device_fingerprint_v2"] is None


def test_register_device_route_forwards_v2_fingerprint() -> None:
    captured: dict[str, Any] = {}

    def _register(
        session,
        *,
        tenant_id,
        terminal_id,
        public_key_b64,
        device_fingerprint,
        device_fingerprint_v2=None,
    ):
        captured["v2"] = device_fingerprint_v2
        return 77

    client = TestClient(_make_app(_register))
    v2_digest = "sha256v2:" + "b" * 64
    r = client.post(
        "/api/v1/pos/terminals/register-device",
        json={
            "terminal_id": 11,
            "public_key": _fresh_public_key(),
            "device_fingerprint": "sha256:" + "a" * 64,
            "device_fingerprint_v2": v2_digest,
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 200, r.text
    assert captured["v2"] == v2_digest


def test_register_device_route_rejects_malformed_fingerprint() -> None:
    def _register(*_a, **_k):  # pragma: no cover — should not be reached
        raise AssertionError("register_device should not be called with bad input")

    client = TestClient(_make_app(_register))
    r = client.post(
        "/api/v1/pos/terminals/register-device",
        json={
            "terminal_id": 11,
            "public_key": _fresh_public_key(),
            "device_fingerprint": "not-a-sha256",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 422


def test_register_device_route_rejects_malformed_v2_fingerprint() -> None:
    def _register(*_a, **_k):  # pragma: no cover — should not be reached
        raise AssertionError("register_device should not be called with bad input")

    client = TestClient(_make_app(_register))
    r = client.post(
        "/api/v1/pos/terminals/register-device",
        json={
            "terminal_id": 11,
            "public_key": _fresh_public_key(),
            "device_fingerprint": "sha256:" + "a" * 64,
            "device_fingerprint_v2": "sha256v2:not-hex",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 422
