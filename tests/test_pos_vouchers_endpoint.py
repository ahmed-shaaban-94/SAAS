"""HTTP-level tests for the POS voucher router.

Mounts only ``vouchers.router`` and overrides auth + service dependencies.
Covers create, list, and validate endpoints including their auth + 404 paths.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_plan_limits, get_voucher_service
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.models import (
    VoucherResponse,
    VoucherStatus,
    VoucherType,
    VoucherValidateResponse,
)
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit


MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


def _make_app(
    service: MagicMock,
    *,
    with_auth: bool = True,
) -> FastAPI:
    from datapulse.api.routes.vouchers import router as voucher_router

    app = FastAPI()
    app.include_router(voucher_router, prefix="/api/v1")
    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="test-user",
        role_key="admin",
        permissions={"pos:voucher:manage", "pos:voucher:validate"},
    )
    if with_auth:
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    else:
        # Force auth to fail — mimic real behaviour by raising 401
        def _no_auth():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = _no_auth
    app.dependency_overrides[get_voucher_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: ctx
    return app


@pytest.fixture()
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service))


def _voucher(**overrides) -> VoucherResponse:
    base = {
        "id": 1,
        "tenant_id": 1,
        "code": "SAVE10",
        "discount_type": VoucherType.amount,
        "value": Decimal("10"),
        "max_uses": 1,
        "uses": 0,
        "status": VoucherStatus.active,
        "starts_at": None,
        "ends_at": None,
        "min_purchase": None,
        "redeemed_txn_id": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return VoucherResponse(**base)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_post_create_returns_201(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.create.return_value = _voucher(id=9, code="NEW10")
    resp = client.post(
        "/api/v1/pos/vouchers",
        json={
            "code": "NEW10",
            "discount_type": "amount",
            "value": 10,
            "max_uses": 1,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "NEW10"
    assert resp.json()["id"] == 9


def test_post_create_without_auth_returns_401(mock_service: MagicMock) -> None:
    app = _make_app(mock_service, with_auth=False)
    client_no_auth = TestClient(app)
    resp = client_no_auth.post(
        "/api/v1/pos/vouchers",
        json={"code": "X10", "discount_type": "amount", "value": 10},
    )
    assert resp.status_code == 401


def test_post_create_percent_over_100_returns_422(
    client: TestClient, mock_service: MagicMock
) -> None:
    resp = client.post(
        "/api/v1/pos/vouchers",
        json={"code": "BAD", "discount_type": "percent", "value": 150},
    )
    assert resp.status_code == 422


def test_post_create_invalid_code_pattern_returns_422(
    client: TestClient, mock_service: MagicMock
) -> None:
    resp = client.post(
        "/api/v1/pos/vouchers",
        # lowercase + spaces violate the ^[A-Z0-9_-]+$ pattern
        json={"code": "save 10", "discount_type": "amount", "value": 5},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_get_list_returns_tenant_vouchers(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list.return_value = [_voucher(id=1), _voucher(id=2, code="OTHER")]
    resp = client.get("/api/v1/pos/vouchers")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_list_applies_status_filter(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list.return_value = []
    client.get("/api/v1/pos/vouchers?status=redeemed")
    _, kwargs = mock_service.list.call_args
    assert kwargs["status"] == VoucherStatus.redeemed


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def test_post_validate_active_code_returns_200(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.validate.return_value = VoucherValidateResponse(
        code="SAVE10",
        discount_type=VoucherType.amount,
        value=Decimal("10"),
        remaining_uses=3,
        expires_at=None,
        min_purchase=None,
    )
    resp = client.post("/api/v1/pos/vouchers/validate", json={"code": "SAVE10"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "SAVE10"
    assert body["remaining_uses"] == 3


def test_post_validate_unknown_code_returns_404(
    client: TestClient, mock_service: MagicMock
) -> None:
    mock_service.validate.side_effect = HTTPException(status_code=404, detail="voucher_not_found")
    resp = client.post("/api/v1/pos/vouchers/validate", json={"code": "NOPE"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "voucher_not_found"


def test_post_validate_with_cart_subtotal_below_min_purchase_returns_400(
    client: TestClient, mock_service: MagicMock
) -> None:
    mock_service.validate.side_effect = HTTPException(
        status_code=400, detail="voucher_min_purchase_unmet"
    )
    resp = client.post(
        "/api/v1/pos/vouchers/validate",
        json={"code": "SAVE10", "cart_subtotal": 20},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "voucher_min_purchase_unmet"
