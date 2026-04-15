"""HTTP-level tests for the POS API router (B3 endpoints).

A minimal FastAPI app mounts only ``pos.router`` and overrides the auth +
service dependencies. Exception handlers are explicitly registered so the
tests verify the full HTTP status mapping for POS errors.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service, get_tenant_plan_limits
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.pos.constants import (
    PaymentMethod,
    TerminalStatus,
    TransactionStatus,
)
from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    TerminalNotActiveError,
)
from datapulse.pos.models import (
    CheckoutResponse,
    PosCartItem,
    PosProductResult,
    PosStockInfo,
    TerminalSession,
    TransactionResponse,
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


def _make_app(service: MagicMock) -> FastAPI:
    """Build a minimal app with only the POS router + the exception handlers."""
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()
    app.include_router(pos_router, prefix="/api/v1")
    _ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="test-user",
        role_key="admin",
        permissions={
            "pos:terminal:open", "pos:transaction:create", "pos:transaction:void",
            "pos:return:create", "pos:shift:reconcile", "pos:shift:open",
            "pos:controlled:verify",
        },
    )
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: _ctx

    # Replicate the production exception -> status mapping for these tests
    @app.exception_handler(InsufficientStockError)
    async def _h1(_req: Request, exc: InsufficientStockError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(TerminalNotActiveError)
    async def _h2(_req: Request, exc: TerminalNotActiveError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(PharmacistVerificationRequiredError)
    async def _h3(_req: Request, exc: PharmacistVerificationRequiredError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    return app


@pytest.fixture()
def mock_service() -> MagicMock:
    """A MagicMock with AsyncMock attached to async-only service methods."""
    svc = MagicMock()
    svc.add_item = AsyncMock()
    svc.checkout = AsyncMock()
    svc.get_stock_info = AsyncMock()
    return svc


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    return TestClient(_make_app(mock_service))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _terminal_session(status: TerminalStatus = TerminalStatus.open) -> TerminalSession:
    return TerminalSession(
        id=1,
        tenant_id=1,
        site_code="SITE01",
        staff_id="staff-1",
        terminal_name="Terminal-1",
        status=status,
        opened_at=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
        closed_at=None,
        opening_cash=Decimal("100"),
        closing_cash=None,
    )


def _transaction_response() -> TransactionResponse:
    return TransactionResponse(
        id=100,
        terminal_id=1,
        staff_id="staff-1",
        customer_id=None,
        grand_total=Decimal("0"),
        payment_method=None,
        status=TransactionStatus.draft,
        receipt_number=None,
        created_at=datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
    )


def _cart_item() -> PosCartItem:
    return PosCartItem(
        drug_code="DRUG001",
        drug_name="Paracetamol",
        batch_number="BATCH-NEW",
        expiry_date=None,
        quantity=Decimal("3"),
        unit_price=Decimal("12.5"),
        discount=Decimal("0"),
        line_total=Decimal("37.5"),
        is_controlled=False,
        pharmacist_id=None,
    )


# ---------------------------------------------------------------------------
# Terminals
# ---------------------------------------------------------------------------


class TestTerminalRoutes:
    def test_open_terminal_201(self, client: TestClient, mock_service: MagicMock):
        mock_service.open_terminal.return_value = _terminal_session()
        resp = client.post(
            "/api/v1/pos/terminals",
            json={"site_code": "SITE01", "terminal_name": "Terminal-1", "opening_cash": 100},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "open"
        mock_service.open_terminal.assert_called_once()

    def test_get_terminal_404_when_missing(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        mock_service.get_terminal.return_value = None
        assert client.get("/api/v1/pos/terminals/999").status_code == 404

    def test_pause_terminal_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.pause_terminal.return_value = _terminal_session(TerminalStatus.paused)
        resp = client.post("/api/v1/pos/terminals/1/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_pause_terminal_409_on_illegal_transition(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        mock_service.pause_terminal.side_effect = TerminalNotActiveError(
            terminal_id=1,
            current_status="closed",
        )
        resp = client.post("/api/v1/pos/terminals/1/pause")
        assert resp.status_code == 409

    def test_resume_terminal_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.resume_terminal.return_value = _terminal_session(TerminalStatus.active)
        resp = client.post("/api/v1/pos/terminals/1/resume")
        assert resp.status_code == 200

    def test_close_terminal_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.close_terminal.return_value = _terminal_session(TerminalStatus.closed)
        resp = client.post(
            "/api/v1/pos/terminals/1/close",
            json={"closing_cash": 250},
        )
        assert resp.status_code == 200

    def test_list_active_terminals_200(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        mock_service.list_active_terminals.return_value = [
            _terminal_session(TerminalStatus.active),
        ]
        resp = client.get("/api/v1/pos/terminals/active")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TestTransactionRoutes:
    def test_create_transaction_201(self, client: TestClient, mock_service: MagicMock):
        mock_service.create_transaction.return_value = _transaction_response()
        resp = client.post("/api/v1/pos/transactions?terminal_id=1&site_code=SITE01")
        assert resp.status_code == 201

    def test_create_transaction_409_when_terminal_paused(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        mock_service.create_transaction.side_effect = TerminalNotActiveError(
            terminal_id=1,
            current_status="paused",
        )
        resp = client.post("/api/v1/pos/transactions?terminal_id=1&site_code=SITE01")
        assert resp.status_code == 409

    def test_get_transaction_200(self, client: TestClient, mock_service: MagicMock):
        from datapulse.pos.models import TransactionDetailResponse

        mock_service.get_transaction_detail.return_value = TransactionDetailResponse(
            id=100,
            terminal_id=1,
            staff_id="staff-1",
            site_code="SITE01",
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            status=TransactionStatus.draft,
            created_at=datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
            items=[],
        )
        resp = client.get("/api/v1/pos/transactions/100")
        assert resp.status_code == 200

    def test_get_transaction_404(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_transaction_detail.return_value = None
        assert client.get("/api/v1/pos/transactions/999").status_code == 404

    def test_list_transactions_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.list_transactions.return_value = [_transaction_response()]
        resp = client.get("/api/v1/pos/transactions?limit=10")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_add_item_201(self, client: TestClient, mock_service: MagicMock):
        # detail lookup needed for site_code resolution
        from datapulse.pos.models import TransactionDetailResponse

        mock_service.get_transaction_detail.return_value = TransactionDetailResponse(
            id=100,
            terminal_id=1,
            staff_id="staff-1",
            site_code="SITE01",
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            status=TransactionStatus.draft,
            created_at=datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
            items=[],
        )
        mock_service.add_item.return_value = _cart_item()
        resp = client.post(
            "/api/v1/pos/transactions/100/items",
            json={"drug_code": "DRUG001", "quantity": "3"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["drug_code"] == "DRUG001"

    def test_add_item_409_insufficient_stock(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        from datapulse.pos.models import TransactionDetailResponse

        mock_service.get_transaction_detail.return_value = TransactionDetailResponse(
            id=100,
            terminal_id=1,
            staff_id="s",
            site_code="SITE01",
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            status=TransactionStatus.draft,
            created_at=datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
            items=[],
        )
        mock_service.add_item.side_effect = InsufficientStockError(
            "DRUG001",
            Decimal("5"),
            Decimal("3"),
        )
        resp = client.post(
            "/api/v1/pos/transactions/100/items",
            json={"drug_code": "DRUG001", "quantity": "5"},
        )
        assert resp.status_code == 409

    def test_add_item_403_pharmacist_required(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        from datapulse.pos.models import TransactionDetailResponse

        mock_service.get_transaction_detail.return_value = TransactionDetailResponse(
            id=100,
            terminal_id=1,
            staff_id="s",
            site_code="SITE01",
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            status=TransactionStatus.draft,
            created_at=datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
            items=[],
        )
        mock_service.add_item.side_effect = PharmacistVerificationRequiredError(
            "MORPHINE",
            "narcotic",
        )
        resp = client.post(
            "/api/v1/pos/transactions/100/items",
            json={"drug_code": "MORPHINE", "quantity": "1"},
        )
        assert resp.status_code == 403

    def test_remove_item_204(self, client: TestClient, mock_service: MagicMock):
        mock_service.remove_item.return_value = True
        resp = client.delete("/api/v1/pos/transactions/100/items/1")
        assert resp.status_code == 204

    def test_remove_item_404(self, client: TestClient, mock_service: MagicMock):
        mock_service.remove_item.return_value = False
        resp = client.delete("/api/v1/pos/transactions/100/items/99")
        assert resp.status_code == 404

    def test_checkout_returns_response(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ):
        mock_service.checkout.return_value = CheckoutResponse(
            transaction_id=100,
            receipt_number="R20260415-1-100",
            grand_total=Decimal("75"),
            payment_method=PaymentMethod.cash,
            change_due=Decimal("25"),
            status=TransactionStatus.completed,
        )
        resp = client.post(
            "/api/v1/pos/transactions/100/checkout",
            json={"payment_method": "cash", "cash_tendered": "100"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["receipt_number"] == "R20260415-1-100"
        assert body["payment_method"] == "cash"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


class TestProductRoutes:
    def test_search_products_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.search_products.return_value = [
            PosProductResult(
                drug_code="DRUG001",
                drug_name="Paracetamol",
                drug_brand="Panadol",
                drug_cluster="Analgesic",
                unit_price=Decimal("12.5"),
                stock_quantity=Decimal("0"),
                is_controlled=False,
                requires_pharmacist=False,
            ),
        ]
        resp = client.get("/api/v1/pos/products/search?q=para")
        assert resp.status_code == 200
        assert resp.json()[0]["drug_code"] == "DRUG001"

    def test_search_requires_query(self, client: TestClient):
        resp = client.get("/api/v1/pos/products/search")
        # Missing required `q` should be 422
        assert resp.status_code == 422

    def test_get_stock_info_200(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_stock_info.return_value = PosStockInfo(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_available=Decimal("100"),
            batches=[],
        )
        resp = client.get("/api/v1/pos/products/DRUG001/stock?site_code=SITE01")
        assert resp.status_code == 200
        # JsonDecimal serialises to a JSON number on the wire
        assert Decimal(str(resp.json()["quantity_available"])) == Decimal("100")

    def test_get_stock_info_requires_site_code(self, client: TestClient):
        resp = client.get("/api/v1/pos/products/DRUG001/stock")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Catch-all dependency override sanity
# ---------------------------------------------------------------------------


def test_app_isolated_from_real_db(client: TestClient, mock_service: MagicMock) -> None:
    """A smoke check: any endpoint hits the mocked service, never the DB."""
    mock_service.list_active_terminals.return_value = []
    resp = client.get("/api/v1/pos/terminals/active")
    assert resp.status_code == 200
    assert resp.json() == []


def _ignored_for_typing(_: Any) -> None:
    """Keep ``Any`` import live without affecting runtime (silence lint)."""
    return None
