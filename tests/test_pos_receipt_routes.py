"""HTTP-level tests for POS receipt routes.

Covers receipt read/send RBAC plus idempotency for delivery side effects.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import (
    get_pos_service,
    get_tenant_plan_limits,
    get_tenant_session,
)
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.exceptions import WhatsAppDeliveryFailedError, WhatsAppDisabledError
from datapulse.pos.idempotency import IdempotencyContext
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit

MOCK_USER = {
    "sub": "receipt-user",
    "email": "receipt@datapulse.local",
    "tenant_id": "1",
    "roles": ["pos_cashier"],
    "raw_claims": {},
}


def _make_app(service: MagicMock, permissions: set[str]) -> FastAPI:
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()
    app.include_router(pos_router, prefix="/api/v1")
    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="receipt-user",
        role_key="pos_cashier",
        permissions=permissions,
    )
    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    app.state.mock_session = session

    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: ctx
    app.dependency_overrides[get_tenant_session] = lambda: session

    @app.exception_handler(WhatsAppDisabledError)
    async def _whatsapp_disabled(_req: Request, exc: WhatsAppDisabledError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @app.exception_handler(WhatsAppDeliveryFailedError)
    async def _whatsapp_failed(_req: Request, exc: WhatsAppDeliveryFailedError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": exc.message})

    return app


def _send_permissions() -> set[str]:
    return {"pos:receipt:read", "pos:receipt:send"}


def test_get_receipt_pdf_requires_read_permission() -> None:
    service = MagicMock()
    service.get_receipt_pdf.return_value = b"%PDF mock"
    app = _make_app(service, permissions=set())

    with TestClient(app) as client:
        resp = client.get("/api/v1/pos/receipts/100")

    assert resp.status_code == 403
    service.get_receipt_pdf.assert_not_called()


def test_get_receipt_pdf_streams_with_read_permission() -> None:
    service = MagicMock()
    service.get_receipt_pdf.return_value = b"%PDF mock"
    app = _make_app(service, permissions={"pos:receipt:read"})

    with TestClient(app) as client:
        resp = client.get("/api/v1/pos/receipts/100")

    assert resp.status_code == 200
    assert resp.content == b"%PDF mock"
    assert resp.headers["content-type"] == "application/pdf"
    service.get_receipt_pdf.assert_called_once_with(100, 1)


def test_whatsapp_receipt_requires_idempotency_key() -> None:
    service = MagicMock()
    app = _make_app(service, permissions=_send_permissions())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/pos/receipts/100/whatsapp",
            json={"phone": "01198765432"},
        )

    assert resp.status_code == 422
    service.send_receipt_whatsapp.assert_not_called()


def test_whatsapp_receipt_records_success_with_tenant_scope() -> None:
    service = MagicMock()
    service.send_receipt_whatsapp.return_value = {
        "sent": True,
        "phone_hash": "abc123",
        "provider_message_id": "msg-1",
    }
    app = _make_app(service, permissions=_send_permissions())

    with (
        patch("datapulse.api.routes._pos_receipts.record_idempotent_success") as record,
        TestClient(app) as client,
    ):
        resp = client.post(
            "/api/v1/pos/receipts/100/whatsapp",
            json={"phone": "01198765432"},
            headers={"Idempotency-Key": "receipt-wa-1"},
        )

    assert resp.status_code == 200
    assert resp.json()["provider_message_id"] == "msg-1"
    args, _kwargs = record.call_args
    assert args[1].key == "receipt-wa-1"
    assert args[1].tenant_id == 1
    assert args[2] == 200
    assert args[3]["phone_hash"] == "abc123"


def test_whatsapp_receipt_replays_cached_failure_without_sending() -> None:
    from datapulse.api.routes._pos_routes_deps import _receipt_whatsapp_idempotency_dep

    service = MagicMock()
    app = _make_app(service, permissions=_send_permissions())

    async def _replay_error(_request: Request) -> IdempotencyContext:
        return IdempotencyContext(
            key="receipt-wa-failed",
            tenant_id=1,
            endpoint="POST /pos/receipts/{id}/whatsapp",
            request_hash="e" * 64,
            replay=True,
            cached_status=503,
            cached_body={"detail": "WhatsApp receipt delivery is not enabled."},
        )

    app.dependency_overrides[_receipt_whatsapp_idempotency_dep] = _replay_error

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/pos/receipts/100/whatsapp",
            json={"phone": "01198765432"},
            headers={"Idempotency-Key": "receipt-wa-failed"},
        )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "WhatsApp receipt delivery is not enabled."
    service.send_receipt_whatsapp.assert_not_called()


def test_email_receipt_requires_idempotency_key() -> None:
    service = MagicMock()
    app = _make_app(service, permissions=_send_permissions())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/pos/receipts/100/email",
            json={"email": "customer@example.com"},
        )

    assert resp.status_code == 422
    service.get_receipt_pdf.assert_not_called()


def test_email_receipt_rejects_invalid_email_before_lookup() -> None:
    service = MagicMock()
    app = _make_app(service, permissions=_send_permissions())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/pos/receipts/100/email",
            json={"email": "not-an-email"},
            headers={"Idempotency-Key": "receipt-email-invalid"},
        )

    assert resp.status_code == 422
    service.get_receipt_pdf.assert_not_called()


def _keep_any(_: Any) -> None:
    return None
