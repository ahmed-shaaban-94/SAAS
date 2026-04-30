"""HTTP-level tests for POS B6a routes — void, returns, shifts, cash events.

A minimal FastAPI app mounts only ``pos.router`` and overrides auth + service.
All tests are unit-marked.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service, get_tenant_plan_limits, get_tenant_session
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.constants import (
    CashDrawerEventType,
    ReturnReason,
)
from datapulse.pos.exceptions import PosError
from datapulse.pos.models import (
    CashDrawerEventResponse,
    ReturnDetailResponse,
    ReturnResponse,
    ShiftRecord,
    ShiftSummaryResponse,
    VoidResponse,
)
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit

MOCK_USER: dict[str, Any] = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


def _make_app(service: MagicMock) -> FastAPI:
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()
    app.include_router(pos_router, prefix="/api/v1")
    _ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="test-user",
        role_key="admin",
        permissions={
            "pos:terminal:open",
            "pos:transaction:create",
            "pos:transaction:void",
            "pos:return:create",
            "pos:shift:reconcile",
            "pos:shift:open",
            "pos:cash:event:create",
            "pos:controlled:verify",
        },
    )
    # Mocked tenant DB session — the close-shift route now invokes
    # enforce_close_guard via Depends(get_tenant_session). scalar()=0
    # → the guard accepts; mappings().first()=None lets repo lookups
    # in the same session return cleanly when other routes touch them.
    _mock_session = MagicMock()
    _execute_result = MagicMock()
    _execute_result.scalar.return_value = 0
    _execute_result.mappings.return_value.first.return_value = None
    _mock_session.execute.return_value = _execute_result
    app.state.mock_session = _mock_session

    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: _ctx
    app.dependency_overrides[get_tenant_session] = lambda: _mock_session

    @app.middleware("http")
    async def _inject_tenant(request, call_next):
        request.state.tenant_id = 1
        return await call_next(request)

    @app.exception_handler(PosError)
    async def _pos_handler(_req: Request, exc: PosError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    return app


@pytest.fixture()
def mock_service() -> MagicMock:
    svc = MagicMock()
    svc.void_transaction = AsyncMock()
    svc.process_return = AsyncMock()
    # close_shift route calls service._repo.get_shift_by_id(shift_id) before
    # enforce_close_guard to resolve tenant_id / terminal_id. Return a real
    # dict so int(...) coercion in the route succeeds.
    svc._repo.get_shift_by_id.return_value = {
        "id": 1,
        "tenant_id": 1,
        "terminal_id": 10,
    }
    return svc


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _void_response() -> VoidResponse:
    return VoidResponse(
        id=99,
        transaction_id=1,
        tenant_id=1,
        voided_by="test-user",
        reason="duplicate sale",
        voided_at=datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
    )


def _return_response() -> ReturnResponse:
    return ReturnResponse(
        id=5,
        original_transaction_id=1,
        return_transaction_id=20,
        refund_amount=Decimal("50"),
        refund_method="cash",
        reason=ReturnReason.wrong_drug,
        created_at=datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
    )


def _shift_record() -> ShiftRecord:
    return ShiftRecord(
        id=1,
        terminal_id=10,
        tenant_id=1,
        staff_id="test-user",
        shift_date=date(2026, 4, 15),
        opened_at=datetime(2026, 4, 15, 8, 0, 0, tzinfo=UTC),
        closed_at=None,
        opening_cash=Decimal("500"),
        closing_cash=None,
        expected_cash=None,
        variance=None,
    )


def _shift_summary() -> ShiftSummaryResponse:
    return ShiftSummaryResponse(
        id=1,
        terminal_id=10,
        staff_id="test-user",
        shift_date=date(2026, 4, 15),
        opened_at=datetime(2026, 4, 15, 8, 0, 0, tzinfo=UTC),
        closed_at=datetime(2026, 4, 15, 18, 0, 0, tzinfo=UTC),
        opening_cash=Decimal("500"),
        closing_cash=Decimal("750"),
        expected_cash=Decimal("750"),
        variance=Decimal("0"),
        transaction_count=5,
        total_sales=Decimal("300"),
    )


def _cash_event() -> CashDrawerEventResponse:
    return CashDrawerEventResponse(
        id=7,
        terminal_id=10,
        event_type=CashDrawerEventType.float,
        amount=Decimal("100"),
        reference_id=None,
        timestamp=datetime(2026, 4, 15, 8, 5, 0, tzinfo=UTC),
    )


def _idem(key: str) -> dict[str, str]:
    return {"Idempotency-Key": key}


# ---------------------------------------------------------------------------
# Void route tests
# ---------------------------------------------------------------------------


def test_void_transaction_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.void_transaction.return_value = _void_response()

    resp = client.post(
        "/api/v1/pos/transactions/1/void",
        json={"reason": "duplicate sale"},
        headers=_idem("void-success"),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 99
    assert data["transaction_id"] == 1
    assert data["voided_by"] == "test-user"
    mock_service.void_transaction.assert_awaited_once()


def test_void_transaction_reason_too_short(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/pos/transactions/1/void",
        json={"reason": "no"},  # min_length=3
        headers=_idem("void-short"),
    )
    assert resp.status_code == 422


def test_void_transaction_requires_idempotency_key(
    client: TestClient,
    mock_service: MagicMock,
) -> None:
    resp = client.post(
        "/api/v1/pos/transactions/1/void",
        json={"reason": "duplicate sale"},
    )
    assert resp.status_code == 422
    mock_service.void_transaction.assert_not_awaited()


def test_void_transaction_conflict(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.void_transaction.side_effect = PosError(
        message="Only completed transactions can be voided",
        detail="",
    )
    resp = client.post(
        "/api/v1/pos/transactions/1/void",
        json={"reason": "test reason"},
        headers=_idem("void-conflict"),
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Return route tests
# ---------------------------------------------------------------------------


def test_process_return_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.process_return.return_value = _return_response()

    payload = {
        "original_transaction_id": 1,
        "items": [
            {
                "drug_code": "DRUG001",
                "drug_name": "Test Drug",
                "batch_number": "BATCH-1",
                "expiry_date": "2027-12-31",
                "quantity": "1",
                "unit_price": "50",
                "discount": "0",
                "line_total": "50",
                "is_controlled": False,
            }
        ],
        "reason": "wrong_drug",
        "refund_method": "cash",
    }
    resp = client.post("/api/v1/pos/returns", json=payload, headers=_idem("return-success"))

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 5
    assert data["refund_amount"] == 50.0
    assert data["reason"] == "wrong_drug"
    mock_service.process_return.assert_awaited_once()


def test_process_return_invalid_refund_method(client: TestClient) -> None:
    payload = {
        "original_transaction_id": 1,
        "items": [],
        "reason": "defective",
        "refund_method": "card",  # not in pattern
    }
    resp = client.post("/api/v1/pos/returns", json=payload, headers=_idem("return-invalid"))
    assert resp.status_code == 422


def test_get_return_found(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_return.return_value = ReturnDetailResponse(
        id=5,
        original_transaction_id=1,
        return_transaction_id=20,
        staff_id="test-user",
        refund_amount=Decimal("50"),
        refund_method="cash",
        reason=ReturnReason.wrong_drug,
        notes=None,
        created_at=datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC),
        items=[],
    )
    resp = client.get("/api/v1/pos/returns/5")
    assert resp.status_code == 200
    assert resp.json()["id"] == 5


def test_get_return_not_found(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_return.return_value = None
    resp = client.get("/api/v1/pos/returns/999")
    assert resp.status_code == 404


def test_list_transaction_returns(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list_returns_for_transaction.return_value = [_return_response()]
    resp = client.get("/api/v1/pos/transactions/1/returns")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_returns(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list_returns.return_value = [_return_response()]
    resp = client.get("/api/v1/pos/returns?limit=10&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    mock_service.list_returns.assert_called_once_with(1, limit=10, offset=0)


# ---------------------------------------------------------------------------
# Shift route tests
# ---------------------------------------------------------------------------


def test_start_shift_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.start_shift.return_value = _shift_record()
    resp = client.post(
        "/api/v1/pos/shifts",
        json={"terminal_id": 10, "opening_cash": "500"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["terminal_id"] == 10
    mock_service.start_shift.assert_called_once()


def test_start_shift_already_open_conflict(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.start_shift.side_effect = PosError(
        message="Terminal 10 already has an open shift",
        detail="",
    )
    resp = client.post(
        "/api/v1/pos/shifts",
        json={"terminal_id": 10, "opening_cash": "0"},
    )
    assert resp.status_code == 409


def test_list_shifts(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list_shifts.return_value = [_shift_record()]
    resp = client.get("/api/v1/pos/shifts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_current_shift_found(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_current_shift.return_value = _shift_record()
    resp = client.get("/api/v1/pos/shifts/current/10")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_current_shift_not_found(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_current_shift.return_value = None
    resp = client.get("/api/v1/pos/shifts/current/99")
    assert resp.status_code == 404


def test_close_shift_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_shift_by_id.return_value = _shift_record()
    mock_service.close_shift.return_value = _shift_summary()
    resp = client.post(
        "/api/v1/pos/shifts/1/close",
        json={
            "closing_cash": "750",
            "local_unresolved": {"count": 0, "digest": "empty-queue"},
        },
        headers=_idem("shift-close-success"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_count"] == 5
    assert data["total_sales"] == 300.0
    assert data["variance"] == 0.0


def test_close_shift_already_closed(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_shift_by_id.return_value = _shift_record()
    mock_service.close_shift.side_effect = PosError(
        message="Shift 1 is already closed",
        detail="",
    )
    resp = client.post(
        "/api/v1/pos/shifts/1/close",
        json={
            "closing_cash": "750",
            "local_unresolved": {"count": 0, "digest": "empty-queue"},
        },
        headers=_idem("shift-close-conflict"),
    )
    assert resp.status_code == 409


def test_close_shift_requires_unresolved_queue_claim(
    client: TestClient,
    mock_service: MagicMock,
) -> None:
    resp = client.post(
        "/api/v1/pos/shifts/1/close",
        json={"closing_cash": "750"},
        headers=_idem("shift-close-missing-claim"),
    )
    assert resp.status_code == 422
    mock_service.close_shift.assert_not_called()


def test_close_shift_rejects_nonzero_unresolved_claim(
    client: TestClient,
    mock_service: MagicMock,
) -> None:
    mock_service.get_shift_by_id.return_value = _shift_record()
    resp = client.post(
        "/api/v1/pos/shifts/1/close",
        json={
            "closing_cash": "750",
            "local_unresolved": {"count": 2, "digest": "pending-two"},
        },
        headers=_idem("shift-close-unresolved"),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "provisional_work_pending"
    mock_service.close_shift.assert_not_called()


def test_close_shift_guard_rejection_records_idempotent_response(
    client: TestClient,
    mock_service: MagicMock,
) -> None:
    """Guard rejections must be committed for retry replay and forensic audit."""
    mock_service.get_shift_by_id.return_value = _shift_record()
    with patch("datapulse.api.routes._pos_shifts.record_idempotent_exception") as record:
        resp = client.post(
            "/api/v1/pos/shifts/1/close",
            json={
                "closing_cash": "750",
                "local_unresolved": {"count": 2, "digest": "pending-two"},
            },
            headers=_idem("shift-close-unresolved-recorded"),
        )

    assert resp.status_code == 409
    record.assert_called_once()
    args, kwargs = record.call_args
    assert args[1].key == "shift-close-unresolved-recorded"
    assert args[1].tenant_id == 1
    assert isinstance(args[2], PosError)
    assert args[2].message == "provisional_work_pending"
    assert kwargs == {}


def test_pos_tenant_helper_rejects_invalid_tenant_id() -> None:
    from datapulse.api.routes._pos_routes_deps import _tenant_id_of

    with pytest.raises(HTTPException) as exc_info:
        _tenant_id_of({**MOCK_USER, "tenant_id": "tenant-a"})

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid tenant context"


# ---------------------------------------------------------------------------
# Cash event route tests
# ---------------------------------------------------------------------------


def test_record_cash_event_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.record_cash_event.return_value = _cash_event()
    resp = client.post(
        "/api/v1/pos/terminals/10/cash-events",
        json={"event_type": "float", "amount": "100"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 7
    assert data["event_type"] == "float"
    assert data["amount"] == 100.0


def test_record_cash_event_invalid_type(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/pos/terminals/10/cash-events",
        json={"event_type": "unknown", "amount": "100"},
    )
    assert resp.status_code == 422


def test_list_cash_events(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_cash_events.return_value = [_cash_event()]
    resp = client.get("/api/v1/pos/terminals/10/cash-events?limit=50")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    mock_service.get_cash_events.assert_called_once_with(10, tenant_id=1, limit=50)


def test_list_cash_events_default_limit(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_cash_events.return_value = []
    resp = client.get("/api/v1/pos/terminals/10/cash-events")
    assert resp.status_code == 200
    mock_service.get_cash_events.assert_called_once_with(10, tenant_id=1, limit=100)
