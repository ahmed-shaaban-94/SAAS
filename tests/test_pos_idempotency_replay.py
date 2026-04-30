"""Integration test: offline queue replay simulation (issue #733).

Simulates 5 consecutive add_item calls with the same Idempotency-Key
(as an offline queue would send on reconnect). Only the first call should
mutate state; the remaining 4 should replay the cached response.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import (
    get_pos_service,
    get_tenant_plan_limits,
    get_tenant_session,
)
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.constants import TransactionStatus
from datapulse.pos.idempotency import IdempotencyContext
from datapulse.pos.models import PosCartItem, TransactionDetailResponse
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit

MOCK_USER = {
    "sub": "queue-user",
    "email": "queue@datapulse.local",
    "tenant_id": "1",
    "roles": ["pos_cashier"],
    "raw_claims": {},
}


def _make_replay_app(service: MagicMock, replay_after_first: bool = True) -> FastAPI:
    """Build a minimal app where the idempotency dep replays after the first call."""
    from datapulse.api.routes._pos_routes_deps import (
        _add_item_idempotency_dep as _idem_dep,
    )
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()
    app.include_router(pos_router, prefix="/api/v1")
    _ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="queue-user",
        role_key="pos_cashier",
        permissions={
            "pos:transaction:create",
            "pos:transaction:checkout",
        },
    )
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: _ctx

    _session = MagicMock()
    _session.execute.return_value.mappings.return_value.first.return_value = None
    app.dependency_overrides[get_tenant_session] = lambda: _session

    # The idempotency dep is a stateful counter: first call is fresh, rest replay.
    _call_count = [0]
    _cached_body: dict[str, Any] = PosCartItem(
        drug_code="DRUG001",
        drug_name="Paracetamol",
        batch_number="BATCH-Q",
        expiry_date=None,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        discount=Decimal("0"),
        line_total=Decimal("20"),
        is_controlled=False,
        pharmacist_id=None,
    ).model_dump(mode="json")

    async def _stateful_dep(request: Request) -> IdempotencyContext:  # noqa: ARG001
        _call_count[0] += 1
        is_replay = replay_after_first and _call_count[0] > 1
        return IdempotencyContext(
            key="offline-queue-key",
            tenant_id=1,
            endpoint="POST /pos/transactions/{id}/items",
            request_hash="d" * 64,
            replay=is_replay,
            cached_status=200 if is_replay else None,
            cached_body=_cached_body if is_replay else None,
        )

    app.dependency_overrides[_idem_dep] = _stateful_dep
    return app


@pytest.fixture()
def mock_service() -> MagicMock:
    svc = MagicMock()
    svc.add_item = AsyncMock()
    svc.checkout = AsyncMock()
    return svc


def test_offline_queue_replay_five_calls_idempotent(mock_service: MagicMock) -> None:
    """5 consecutive add_item calls with the same key: 1 mutation, 4 replays.

    Simulates a mobile/offline queue that queues the same mutation and sends
    it 5 times on reconnect. Each call returns 201 with the same body, but the
    service is only invoked once.
    """
    txn_detail = TransactionDetailResponse(
        id=42,
        terminal_id=1,
        staff_id="queue-user",
        site_code="SITE01",
        subtotal=Decimal("0"),
        discount_total=Decimal("0"),
        tax_total=Decimal("0"),
        grand_total=Decimal("0"),
        status=TransactionStatus.draft,
        created_at=datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        items=[],
    )
    mock_service.get_transaction_detail.return_value = txn_detail
    mock_service.add_item.return_value = PosCartItem(
        drug_code="DRUG001",
        drug_name="Paracetamol",
        batch_number="BATCH-Q",
        expiry_date=None,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        discount=Decimal("0"),
        line_total=Decimal("20"),
        is_controlled=False,
        pharmacist_id=None,
    )

    app = _make_replay_app(mock_service)
    responses = []
    with TestClient(app) as c:
        for _i in range(5):
            resp = c.post(
                "/api/v1/pos/transactions/42/items",
                json={"drug_code": "DRUG001", "quantity": "2"},
                headers={"Idempotency-Key": "offline-queue-key"},
            )
            responses.append(resp)

    # All 5 should succeed
    for resp in responses:
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    # All 5 should return the same drug_code
    bodies = [r.json()["drug_code"] for r in responses]
    assert all(b == "DRUG001" for b in bodies), f"Unexpected bodies: {bodies}"

    # Service must only be called ONCE (the first call was fresh)
    assert mock_service.add_item.call_count == 1, (
        f"Expected 1 service call, got {mock_service.add_item.call_count}"
    )


def test_unique_keys_each_call_all_mutate(mock_service: MagicMock) -> None:
    """5 calls with distinct keys each invoke the service (normal, non-replay)."""

    txn_detail = TransactionDetailResponse(
        id=42,
        terminal_id=1,
        staff_id="queue-user",
        site_code="SITE01",
        subtotal=Decimal("0"),
        discount_total=Decimal("0"),
        tax_total=Decimal("0"),
        grand_total=Decimal("0"),
        status=TransactionStatus.draft,
        created_at=datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        items=[],
    )
    mock_service.get_transaction_detail.return_value = txn_detail
    mock_service.add_item.return_value = PosCartItem(
        drug_code="DRUG001",
        drug_name="Paracetamol",
        batch_number="BATCH-Q",
        expiry_date=None,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        discount=Decimal("0"),
        line_total=Decimal("20"),
        is_controlled=False,
        pharmacist_id=None,
    )

    # Use the default app (no replay override) — session mock returns None (fresh key each time)
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()
    app.include_router(pos_router, prefix="/api/v1")
    _ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="queue-user",
        role_key="pos_cashier",
        permissions={"pos:transaction:create"},
    )
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: mock_service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: _ctx
    _session = MagicMock()
    _session.execute.return_value.mappings.return_value.first.return_value = None
    app.dependency_overrides[get_tenant_session] = lambda: _session

    with TestClient(app) as c:
        for i in range(5):
            resp = c.post(
                "/api/v1/pos/transactions/42/items",
                json={"drug_code": "DRUG001", "quantity": "2"},
                headers={"Idempotency-Key": f"unique-key-{i}"},
            )
            assert resp.status_code == 201

    assert mock_service.add_item.call_count == 5
