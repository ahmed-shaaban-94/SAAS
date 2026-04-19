"""HTTP-level tests for the POS promotion router.

Mounts only ``promotions.router`` and overrides auth + service dependencies.
Covers create, list, get, update, status, and eligible endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_promotion_service, get_tenant_plan_limits
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.models import (
    EligiblePromotion,
    EligiblePromotionsResponse,
    PromotionDiscountType,
    PromotionResponse,
    PromotionScope,
    PromotionStatus,
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


def _make_app(service: MagicMock, *, with_auth: bool = True) -> FastAPI:
    from datapulse.api.routes.promotions import router as promotions_router

    app = FastAPI()
    app.include_router(promotions_router, prefix="/api/v1")
    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="test-user",
        role_key="admin",
        permissions={"pos:promotion:manage", "pos:promotion:apply"},
    )
    if with_auth:
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    else:

        def _no_auth():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = _no_auth
    app.dependency_overrides[get_promotion_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: ctx
    return app


@pytest.fixture()
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service))


def _promo(**overrides) -> PromotionResponse:
    base = {
        "id": 1,
        "tenant_id": 1,
        "name": "Ramadan",
        "description": None,
        "discount_type": PromotionDiscountType.amount,
        "value": Decimal("10"),
        "scope": PromotionScope.all,
        "starts_at": datetime.now(UTC) - timedelta(days=1),
        "ends_at": datetime.now(UTC) + timedelta(days=30),
        "min_purchase": None,
        "max_discount": None,
        "status": PromotionStatus.paused,
        "scope_items": [],
        "scope_categories": [],
        "usage_count": 0,
        "total_discount_given": Decimal("0"),
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return PromotionResponse(**base)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_promotion_returns_201(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.create.return_value = _promo(id=42, name="Ramadan")
    resp = client.post(
        "/api/v1/pos/promotions",
        json={
            "name": "Ramadan",
            "discount_type": "amount",
            "value": 10,
            "scope": "all",
            "starts_at": "2026-04-20T00:00:00+00:00",
            "ends_at": "2026-05-20T00:00:00+00:00",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == 42
    assert resp.json()["status"] == "paused"


def test_create_promotion_items_scope_requires_items(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/pos/promotions",
        json={
            "name": "X",
            "discount_type": "percent",
            "value": 15,
            "scope": "items",
            "starts_at": "2026-04-20T00:00:00+00:00",
            "ends_at": "2026-05-20T00:00:00+00:00",
            "scope_items": [],
        },
    )
    assert resp.status_code == 422  # pydantic validator


def test_create_promotion_rejects_inverted_dates(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/pos/promotions",
        json={
            "name": "X",
            "discount_type": "amount",
            "value": 5,
            "scope": "all",
            "starts_at": "2026-05-20T00:00:00+00:00",
            "ends_at": "2026-04-20T00:00:00+00:00",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# list / get / status
# ---------------------------------------------------------------------------


def test_list_promotions_returns_payload(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list.return_value = [_promo(id=1), _promo(id=2)]
    resp = client.get("/api/v1/pos/promotions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_promotions_passes_status_filter(
    client: TestClient, mock_service: MagicMock
) -> None:
    mock_service.list.return_value = []
    client.get("/api/v1/pos/promotions?status=active")
    _, kwargs = mock_service.list.call_args
    assert kwargs["status"] == PromotionStatus.active


def test_get_promotion_404(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get.return_value = None
    resp = client.get("/api/v1/pos/promotions/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "promotion_not_found"


def test_set_promotion_status_active(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.set_status.return_value = _promo(status=PromotionStatus.active)
    resp = client.patch(
        "/api/v1/pos/promotions/1/status",
        json={"status": "active"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_set_promotion_status_rejects_expired(client: TestClient) -> None:
    """The StatusUpdate model literal forbids 'expired'."""
    resp = client.patch(
        "/api/v1/pos/promotions/1/status",
        json={"status": "expired"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# eligible
# ---------------------------------------------------------------------------


def test_list_eligible_promotions(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list_eligible.return_value = EligiblePromotionsResponse(
        promotions=[
            EligiblePromotion(
                id=1,
                name="Ramadan",
                description=None,
                discount_type=PromotionDiscountType.percent,
                value=Decimal("10"),
                scope=PromotionScope.all,
                min_purchase=None,
                max_discount=None,
                ends_at=datetime.now(UTC) + timedelta(days=1),
                preview_discount=Decimal("20.0000"),
            )
        ]
    )
    resp = client.post(
        "/api/v1/pos/promotions/eligible",
        json={
            "items": [
                {
                    "drug_code": "A",
                    "drug_cluster": None,
                    "quantity": 1,
                    "unit_price": 200,
                }
            ],
            "subtotal": 200,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["promotions"]) == 1
    assert body["promotions"][0]["preview_discount"] == 20.0


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


def test_create_promotion_requires_auth() -> None:
    service = MagicMock()
    app = _make_app(service, with_auth=False)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/pos/promotions",
        json={
            "name": "X",
            "discount_type": "amount",
            "value": 5,
            "scope": "all",
            "starts_at": "2026-04-20T00:00:00+00:00",
            "ends_at": "2026-05-20T00:00:00+00:00",
        },
    )
    assert resp.status_code == 401
