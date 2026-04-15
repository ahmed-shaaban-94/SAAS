"""POS API endpoints — terminal sessions, transactions, items, checkout, search.

Mounted at ``/api/v1/pos`` and gated by the ``feature_platform`` setting flag.
All endpoints require an authenticated user (RLS handles tenant isolation).

Endpoint groups
---------------
* **Terminals** (5)  — open / get / list-active / pause / resume / close
* **Transactions** (7) — create / get / list / add-item / update-item /
  remove-item / checkout
* **Products** (2) — search / stock-info

Rate limits: 60/min for reads, 30/min for mutations (per the B3 plan).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service
from datapulse.api.limiter import limiter
from datapulse.pos.models import (
    AddItemRequest,
    CheckoutRequest,
    CheckoutResponse,
    PosCartItem,
    PosProductResult,
    PosStockInfo,
    TerminalCloseRequest,
    TerminalOpenRequest,
    TerminalSessionResponse,
    TransactionDetailResponse,
    TransactionResponse,
    UpdateItemRequest,
)
from datapulse.pos.service import PosService

router = APIRouter(
    prefix="/pos",
    tags=["pos"],
    dependencies=[Depends(get_current_user)],
)

ServiceDep = Annotated[PosService, Depends(get_pos_service)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _tenant_id_of(user: CurrentUser) -> int:
    """Coerce the JWT ``tenant_id`` claim to int; defaults to 1 in dev."""
    return int(user.get("tenant_id") or 1)


def _staff_id_of(user: CurrentUser) -> str:
    """Resolve a staff identifier from the JWT (sub, then email)."""
    return str(user.get("sub") or user.get("email") or "unknown")


# ──────────────────────────────────────────────────────────────────────────────
# Terminals
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/terminals",
    response_model=TerminalSessionResponse,
    status_code=201,
)
@limiter.limit("30/minute")
def open_terminal(
    request: Request,
    body: TerminalOpenRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Open a fresh POS terminal session (cashier shift)."""
    session = service.open_terminal(
        tenant_id=_tenant_id_of(user),
        site_code=body.site_code,
        staff_id=_staff_id_of(user),
        terminal_name=body.terminal_name,
        opening_cash=Decimal(str(body.opening_cash)),
    )
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.get("/terminals/active", response_model=list[TerminalSessionResponse])
@limiter.limit("60/minute")
def list_active_terminals(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
) -> list[TerminalSessionResponse]:
    """List all non-closed terminals for the tenant."""
    sessions = service.list_active_terminals(_tenant_id_of(user))
    return [TerminalSessionResponse.model_validate(s.model_dump()) for s in sessions]


@router.get("/terminals/{terminal_id}", response_model=TerminalSessionResponse)
@limiter.limit("60/minute")
def get_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Fetch a single terminal session by ID."""
    _ = user  # tenant scoped via RLS
    session = service.get_terminal(terminal_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Terminal {terminal_id} not found")
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.post(
    "/terminals/{terminal_id}/pause",
    response_model=TerminalSessionResponse,
)
@limiter.limit("30/minute")
def pause_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Pause a terminal — operator stepped away; blocks new transactions."""
    _ = user
    session = service.pause_terminal(terminal_id)
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.post(
    "/terminals/{terminal_id}/resume",
    response_model=TerminalSessionResponse,
)
@limiter.limit("30/minute")
def resume_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Resume a paused terminal back to ``active`` state."""
    _ = user
    session = service.resume_terminal(terminal_id)
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.post(
    "/terminals/{terminal_id}/close",
    response_model=TerminalSessionResponse,
)
@limiter.limit("30/minute")
def close_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    body: TerminalCloseRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Close a terminal — records closing cash and seals the shift."""
    _ = user
    session = service.close_terminal(terminal_id, closing_cash=Decimal(str(body.closing_cash)))
    return TerminalSessionResponse.model_validate(session.model_dump())


# ──────────────────────────────────────────────────────────────────────────────
# Transactions
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=201,
)
@limiter.limit("30/minute")
def create_transaction(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    terminal_id: Annotated[int, Query(ge=1)],
    site_code: Annotated[str, Query(min_length=1, max_length=50)],
    customer_id: Annotated[str | None, Query(max_length=100)] = None,
    pharmacist_id: Annotated[str | None, Query(max_length=100)] = None,
) -> TransactionResponse:
    """Open a new draft transaction on an active terminal."""
    return service.create_transaction(
        tenant_id=_tenant_id_of(user),
        terminal_id=terminal_id,
        staff_id=_staff_id_of(user),
        site_code=site_code,
        pharmacist_id=pharmacist_id,
        customer_id=customer_id,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
)
@limiter.limit("60/minute")
def get_transaction(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> TransactionDetailResponse:
    """Return a transaction header with its full line items."""
    _ = user
    detail = service.get_transaction_detail(transaction_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return detail


@router.get("/transactions", response_model=list[TransactionResponse])
@limiter.limit("60/minute")
def list_transactions(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    terminal_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TransactionResponse]:
    """List transactions for the tenant with optional filters."""
    return service.list_transactions(
        tenant_id=_tenant_id_of(user),
        terminal_id=terminal_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/transactions/{transaction_id}/items",
    response_model=PosCartItem,
    status_code=201,
)
@limiter.limit("30/minute")
async def add_item(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: AddItemRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> PosCartItem:
    """Add a drug to the active draft transaction (FEFO batch + stock check)."""
    txn = service.get_transaction_detail(transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return await service.add_item(
        transaction_id=transaction_id,
        tenant_id=_tenant_id_of(user),
        site_code=txn.site_code,
        drug_code=body.drug_code,
        quantity=Decimal(str(body.quantity)),
        override_price=(
            Decimal(str(body.override_price)) if body.override_price is not None else None
        ),
        pharmacist_id=body.pharmacist_id,
    )


@router.patch(
    "/transactions/{transaction_id}/items/{item_id}",
    response_model=PosCartItem,
)
@limiter.limit("30/minute")
def update_item(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
    body: UpdateItemRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> PosCartItem:
    """Update an existing line item's quantity / price / discount."""
    _ = user
    _ = transaction_id  # routing-only; item_id is unique
    return service.update_item(
        item_id,
        quantity=Decimal(str(body.quantity)),
        unit_price=Decimal(str(body.override_price)) if body.override_price else Decimal("0"),
        discount=Decimal(str(body.discount)) if body.discount is not None else None,
    )


@router.delete(
    "/transactions/{transaction_id}/items/{item_id}",
    status_code=204,
)
@limiter.limit("30/minute")
def remove_item(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> None:
    """Remove a single line item from a draft transaction."""
    _ = user
    _ = transaction_id
    deleted = service.remove_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@router.post(
    "/transactions/{transaction_id}/checkout",
    response_model=CheckoutResponse,
)
@limiter.limit("30/minute")
async def checkout(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: CheckoutRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> CheckoutResponse:
    """Finalise a draft transaction: totals -> payment -> stock -> bronze write."""
    return await service.checkout(
        transaction_id=transaction_id,
        tenant_id=_tenant_id_of(user),
        request=body,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Product / stock lookups
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/products/search", response_model=list[PosProductResult])
@limiter.limit("60/minute")
def search_products(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=100, alias="q")],
    site_code: Annotated[str | None, Query(max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[PosProductResult]:
    """Search the product catalog by drug code, name, or brand."""
    _ = user
    return service.search_products(q, site_code=site_code, limit=limit)


@router.get(
    "/products/{drug_code}/stock",
    response_model=PosStockInfo,
)
@limiter.limit("60/minute")
async def get_stock_info(
    request: Request,
    drug_code: Annotated[str, Path(min_length=1, max_length=100)],
    service: ServiceDep,
    user: CurrentUser,
    site_code: Annotated[str, Query(min_length=1, max_length=50)],
) -> PosStockInfo:
    """Return live stock + per-batch info for a drug at a site."""
    _ = user
    return await service.get_stock_info(drug_code, site_code)
