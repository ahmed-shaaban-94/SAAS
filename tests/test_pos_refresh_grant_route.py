"""Refresh-grant route tests — POST /pos/shifts/{id}/refresh-grant."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
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
    "sub": "staff-42",
    "email": "cashier@datapulse.local",
    "tenant_id": "1",
    "roles": ["cashier"],
    "raw_claims": {},
}


def _open_shift(shift_id: int = 10) -> MagicMock:
    mock = MagicMock()
    mock.terminal_id = 7
    mock.tenant_id = 1
    mock.closed_at = None
    mock.shift_id = shift_id
    return mock


def _closed_shift(shift_id: int = 10) -> MagicMock:
    mock = _open_shift(shift_id)
    mock.closed_at = datetime.now(UTC)
    return mock


def _fake_envelope() -> dict:
    return {
        "payload": {
            "grant_id": "g-123",
            "terminal_id": 7,
            "tenant_id": 1,
            "device_fingerprint": "fingerprint-abc-1234567890",
            "staff_id": "staff-42",
            "shift_id": 10,
            "issued_at": "2026-04-18T20:00:00Z",
            "offline_expires_at": "2026-04-19T08:00:00Z",
            "role_snapshot": {},
            "override_codes": [],
        },
        "signature_ed25519": "sig-b64",
        "key_id": "key-1",
    }


def _make_app(service_stub: MagicMock) -> FastAPI:
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()

    @app.exception_handler(PosError)
    async def _pos_err(_req: Request, exc: PosError):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.include_router(pos_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: service_stub
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()
    app.dependency_overrides[get_access_context] = lambda: AccessContext(
        tenant_id=1, user_id="staff-42", roles=["cashier"], permissions=set()
    )
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    return app


def test_refresh_grant_returns_envelope_for_open_shift():
    """Happy path: shift exists, is open, envelope is returned."""
    from datapulse.pos.models import OfflineGrantEnvelope

    service = MagicMock()
    service.get_shift_by_id.return_value = _open_shift()

    envelope = OfflineGrantEnvelope.model_validate(_fake_envelope())
    # Route imports issue_grant_for_shift locally (inside the function body), so
    # patch at the source module not the consumer.
    with patch("datapulse.pos.grants.issue_grant_for_shift", return_value=envelope):
        app = _make_app(service)
        client = TestClient(app)
        res = client.post(
            "/api/v1/pos/shifts/10/refresh-grant",
            json={"device_fingerprint": "fingerprint-abc-1234567890", "offline_ttl_hours": 12},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["payload"]["grant_id"] == "g-123"
    assert body["payload"]["shift_id"] == 10


def test_refresh_grant_404_when_shift_not_found():
    service = MagicMock()
    service.get_shift_by_id.return_value = None

    app = _make_app(service)
    client = TestClient(app)
    res = client.post(
        "/api/v1/pos/shifts/999/refresh-grant",
        json={"device_fingerprint": "fingerprint-abc-1234567890"},
    )
    assert res.status_code == 404


def test_refresh_grant_404_when_wrong_tenant():
    """Cross-tenant isolation — shift with tenant_id != caller must 404, not leak."""
    service = MagicMock()
    wrong = _open_shift()
    wrong.tenant_id = 999
    service.get_shift_by_id.return_value = wrong

    app = _make_app(service)
    client = TestClient(app)
    res = client.post(
        "/api/v1/pos/shifts/10/refresh-grant",
        json={"device_fingerprint": "fingerprint-abc-1234567890"},
    )
    assert res.status_code == 404


def test_refresh_grant_409_when_shift_already_closed():
    service = MagicMock()
    service.get_shift_by_id.return_value = _closed_shift()

    app = _make_app(service)
    client = TestClient(app)
    res = client.post(
        "/api/v1/pos/shifts/10/refresh-grant",
        json={"device_fingerprint": "fingerprint-abc-1234567890"},
    )
    assert res.status_code == 409


def test_refresh_grant_422_when_fingerprint_too_short():
    service = MagicMock()
    service.get_shift_by_id.return_value = _open_shift()

    app = _make_app(service)
    client = TestClient(app)
    res = client.post(
        "/api/v1/pos/shifts/10/refresh-grant",
        json={"device_fingerprint": "short"},  # min_length=16
    )
    assert res.status_code == 422


def test_refresh_grant_422_when_ttl_out_of_range():
    service = MagicMock()
    service.get_shift_by_id.return_value = _open_shift()

    app = _make_app(service)
    client = TestClient(app)
    res = client.post(
        "/api/v1/pos/shifts/10/refresh-grant",
        json={"device_fingerprint": "fingerprint-abc-1234567890", "offline_ttl_hours": 1000},
    )
    assert res.status_code == 422
