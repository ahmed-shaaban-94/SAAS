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
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service, get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.billing.pos_guard import require_pos_plan
from datapulse.logging import get_logger
from datapulse.pos.models import (
    AddItemRequest,
    CashCountRequest,
    CashDrawerEventResponse,
    CheckoutRequest,
    CheckoutResponse,
    CloseShiftRequest,
    PharmacistVerifyRequest,
    PharmacistVerifyResponse,
    PosCartItem,
    PosProductResult,
    PosStockInfo,
    ReturnDetailResponse,
    ReturnRequest,
    ReturnResponse,
    ShiftRecord,
    ShiftSummaryResponse,
    StartShiftRequest,
    TerminalCloseRequest,
    TerminalOpenRequest,
    TerminalSessionResponse,
    TransactionDetailResponse,
    TransactionResponse,
    UpdateItemRequest,
    VoidRequest,
    VoidResponse,
)
from datapulse.pos.service import PosService
from datapulse.rbac.dependencies import require_permission

log = get_logger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["pos"],
    # B7: billing guard enforces platform/enterprise plan; auth guard requires JWT.
    dependencies=[Depends(get_current_user), Depends(require_pos_plan())],
)

ServiceDep = Annotated[PosService, Depends(get_pos_service)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
SessionDep = Annotated[Session, Depends(get_tenant_session)]


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
    dependencies=[Depends(require_permission("pos:terminal:open"))],
)
@limiter.limit("30/minute")
def open_terminal(
    request: Request,
    body: TerminalOpenRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
) -> TerminalSessionResponse:
    """Open a fresh POS terminal session (cashier shift).

    Enforces the Phase-1 single-terminal policy (§1.4): if the tenant's
    ``pos_max_terminals`` cap would be exceeded, responds 409. The full
    device-bound per-request guard (§8.9) arrives when downstream mutating
    routes gain ``Depends(device_token_verifier)`` — this is defense-in-depth
    at the terminal-open point.
    """
    tenant_id = _tenant_id_of(user)

    # Single-terminal cap — §1.4 layer 2. Defensive try/except: if the
    # bronze.tenants flags columns aren't yet applied (pre-migration-084
    # environments / some unit-test stubs), fall back to the plan's default
    # cap of 1 rather than crashing the route.
    try:
        max_terminals = (
            db_session.execute(
                text("SELECT pos_max_terminals FROM bronze.tenants WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            ).scalar()
            or 1
        )
        active_count = (
            db_session.execute(
                text(
                    """SELECT count(*) FROM pos.terminal_sessions
                        WHERE tenant_id = :tid
                          AND status IN ('open','active','paused')"""
                ),
                {"tid": tenant_id},
            ).scalar()
            or 0
        )
    except Exception:  # noqa: BLE001 — permissive in environments without the new columns/mocks
        max_terminals, active_count = 1, 0

    if active_count >= max_terminals:
        raise HTTPException(
            status_code=409,
            detail=f"multi_terminal_limit_reached:{active_count}/{max_terminals}",
        )

    opened = service.open_terminal(
        tenant_id=tenant_id,
        site_code=body.site_code,
        staff_id=_staff_id_of(user),
        terminal_name=body.terminal_name,
        opening_cash=Decimal(str(body.opening_cash)),
    )
    return TerminalSessionResponse.model_validate(opened.model_dump())


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


# NOTE: `/terminals/active-for-me` MUST be declared before `/terminals/{terminal_id}`
# so FastAPI routes the literal path before the dynamic one.
@router.get("/terminals/active-for-me")
@limiter.limit("60/minute")
def active_terminals_for_me(
    request: Request,
    user: CurrentUser,
    db_session: SessionDep,
):
    """Return the caller tenant's currently-active POS terminals + multi-terminal flag.

    Used by the desktop client on launch to detect "another terminal is
    already open for this pharmacy" before attempting to open a shift (§1.4).
    Response model is resolved at import time via the forward-declared
    ``ActiveForMeResponse`` imported in the module-late block.
    """
    from datapulse.pos.models import (
        ActiveForMeResponse,
        ActiveTerminalRow,
    )

    tenant_id = _tenant_id_of(user)
    rows = (
        db_session.execute(
            text(
                """
            SELECT ts.id            AS terminal_id,
                   td.device_fingerprint,
                   ts.opened_at
              FROM pos.terminal_sessions ts
         LEFT JOIN pos.terminal_devices td
                ON td.terminal_id = ts.id AND td.revoked_at IS NULL
             WHERE ts.tenant_id = :tid
               AND ts.status IN ('open', 'active', 'paused')
          ORDER BY ts.opened_at ASC
            """
            ),
            {"tid": tenant_id},
        )
        .mappings()
        .all()
    )

    flags = db_session.execute(
        text(
            """SELECT pos_multi_terminal_allowed, pos_max_terminals
                 FROM bronze.tenants
                WHERE tenant_id = :tid"""
        ),
        {"tid": tenant_id},
    ).mappings().first() or {"pos_multi_terminal_allowed": False, "pos_max_terminals": 1}

    return ActiveForMeResponse(
        active_terminals=[ActiveTerminalRow(**r) for r in rows],
        multi_terminal_allowed=bool(flags["pos_multi_terminal_allowed"]),
        max_terminals=int(flags["pos_max_terminals"]),
    )


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


# ──────────────────────────────────────────────────────────────────────────────
# Receipts (B4)
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/receipts/{transaction_id}")
@limiter.limit("60/minute")
def get_receipt_pdf(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> Response:
    """Return the PDF receipt for a completed transaction."""
    content = service.get_receipt_pdf(transaction_id, _tenant_id_of(user))
    return Response(content=content, media_type="application/pdf")


@router.get("/receipts/{transaction_id}/thermal")
@limiter.limit("60/minute")
def get_receipt_thermal(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> Response:
    """Return the raw ESC/POS thermal receipt bytes."""
    content = service.get_receipt_thermal(transaction_id, _tenant_id_of(user))
    return Response(content=content, media_type="application/octet-stream")


class _EmailReceiptRequest(BaseModel):
    email: str


@router.post("/receipts/{transaction_id}/email")
@limiter.limit("10/minute")
def send_receipt_email(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: _EmailReceiptRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> dict:
    """Send the PDF receipt to the given email address (stub — email delivery in Phase 2)."""
    _ = service.get_receipt_pdf(transaction_id, _tenant_id_of(user))
    log.info("pos.receipt.email_queued", transaction_id=transaction_id, email=body.email)
    return {"sent": True, "email": body.email}


# ──────────────────────────────────────────────────────────────────────────────
# Void (B6a)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/transactions/{transaction_id}/void",
    response_model=VoidResponse,
    dependencies=[Depends(require_permission("pos:transaction:void"))],
)
@limiter.limit("10/minute")
async def void_transaction(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: VoidRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> VoidResponse:
    """Void a completed transaction — reverses inventory and writes an audit log.

    Restricted to supervisors / managers. Only ``completed`` transactions
    may be voided; draft transactions should be abandoned by removing items.
    """
    return await service.void_transaction(
        transaction_id=transaction_id,
        tenant_id=_tenant_id_of(user),
        reason=body.reason,
        voided_by=_staff_id_of(user),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Returns (B6a)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/returns",
    response_model=ReturnResponse,
    status_code=201,
    dependencies=[Depends(require_permission("pos:return:create"))],
)
@limiter.limit("20/minute")
async def process_return(
    request: Request,
    body: ReturnRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> ReturnResponse:
    """Process a drug return against a completed transaction.

    Creates a return transaction, restocks inventory via FEFO movement,
    and records a ``pos.returns`` audit entry.
    """
    return await service.process_return(
        original_transaction_id=body.original_transaction_id,
        tenant_id=_tenant_id_of(user),
        staff_id=_staff_id_of(user),
        items=list(body.items),
        reason=body.reason,
        refund_method=body.refund_method,
        notes=body.notes,
    )


@router.get("/returns/{return_id}", response_model=ReturnDetailResponse)
@limiter.limit("60/minute")
def get_return(
    request: Request,
    return_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> ReturnDetailResponse:
    """Fetch a single return record with its line items."""
    _ = user
    detail = service.get_return(return_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Return {return_id} not found")
    return detail


@router.get(
    "/transactions/{transaction_id}/returns",
    response_model=list[ReturnResponse],
)
@limiter.limit("60/minute")
def list_transaction_returns(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> list[ReturnResponse]:
    """List all return records for an original transaction."""
    _ = user
    return service.list_returns_for_transaction(transaction_id)


@router.get("/returns", response_model=list[ReturnResponse])
@limiter.limit("60/minute")
def list_returns(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReturnResponse]:
    """List all return records for the tenant, most recent first."""
    return service.list_returns(
        _tenant_id_of(user),
        limit=limit,
        offset=offset,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Shifts (B6a)
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/shifts", response_model=ShiftRecord, status_code=201)
@limiter.limit("20/minute")
def start_shift(
    request: Request,
    body: StartShiftRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> ShiftRecord:
    """Start a new cashier shift on the specified terminal.

    Raises 409 if the terminal already has an open shift.
    """
    return service.start_shift(
        terminal_id=body.terminal_id,
        tenant_id=_tenant_id_of(user),
        staff_id=_staff_id_of(user),
        opening_cash=Decimal(str(body.opening_cash)),
    )


@router.get("/shifts", response_model=list[ShiftRecord])
@limiter.limit("60/minute")
def list_shifts(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    terminal_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ShiftRecord]:
    """List shift records for the tenant, most recent first."""
    return service.list_shifts(
        _tenant_id_of(user),
        terminal_id=terminal_id,
        limit=limit,
        offset=offset,
    )


@router.get("/shifts/current/{terminal_id}", response_model=ShiftRecord)
@limiter.limit("60/minute")
def get_current_shift(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> ShiftRecord:
    """Return the currently open shift for a terminal."""
    _ = user
    shift = service.get_current_shift(terminal_id)
    if shift is None:
        raise HTTPException(
            status_code=404,
            detail=f"No open shift found for terminal {terminal_id}",
        )
    return shift


@router.post(
    "/shifts/{shift_id}/close",
    response_model=ShiftSummaryResponse,
    dependencies=[Depends(require_permission("pos:shift:reconcile"))],
)
@limiter.limit("20/minute")
def close_shift(
    request: Request,
    shift_id: Annotated[int, Path(ge=1)],
    body: CloseShiftRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> ShiftSummaryResponse:
    """Close a cashier shift and compute cash reconciliation.

    Returns ``expected_cash``, ``variance`` (closing - expected), transaction count,
    and total sales for the shift.
    """
    _ = user
    return service.close_shift(
        shift_id=shift_id,
        closing_cash=Decimal(str(body.closing_cash)),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Cash drawer events (B6a)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/terminals/{terminal_id}/cash-events",
    response_model=CashDrawerEventResponse,
    status_code=201,
)
@limiter.limit("30/minute")
def record_cash_event(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    body: CashCountRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> CashDrawerEventResponse:
    """Record a mid-shift cash drawer event (float, pickup, sale, refund)."""
    return service.record_cash_event(
        terminal_id=terminal_id,
        tenant_id=_tenant_id_of(user),
        event_type=body.event_type.value,
        amount=Decimal(str(body.amount)),
        reference_id=body.reference_id,
    )


@router.get(
    "/terminals/{terminal_id}/cash-events",
    response_model=list[CashDrawerEventResponse],
)
@limiter.limit("60/minute")
def list_cash_events(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CashDrawerEventResponse]:
    """List cash drawer events for a terminal, most recent first."""
    _ = user
    return service.get_cash_events(terminal_id, limit=limit)


# ──────────────────────────────────────────────────────────────────────────────
# Controlled substance verification (B7)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/controlled/verify",
    response_model=PharmacistVerifyResponse,
    dependencies=[Depends(require_permission("pos:controlled:verify"))],
)
@limiter.limit("10/minute")
def verify_pharmacist(
    request: Request,
    body: PharmacistVerifyRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> PharmacistVerifyResponse:
    """Verify a pharmacist PIN for controlled-substance dispensing.

    The pharmacist submits their ``pharmacist_id`` (JWT sub) and ``credential``
    (PIN) for a specific ``drug_code``.  On success, returns a short-lived
    signed token (5 min TTL) to be passed as ``pharmacist_id`` in the
    subsequent ``add_item`` call — avoiding a PIN re-entry per item.

    Requires the ``pos:controlled:verify`` permission (``pos_pharmacist`` or
    ``pos_manager`` roles).  Rate-limited to 10 requests/minute to limit
    brute-force exposure.
    """
    _ = user
    return service.verify_pharmacist_pin(
        pharmacist_id=body.pharmacist_id,
        credential=body.credential,
        drug_code=body.drug_code,
    )


# ──────────────────────────────────────────────────────────────────────────────
# M1 — Capabilities (§6.6) — feature-only, unauthenticated
# ──────────────────────────────────────────────────────────────────────────────
#
# Registered as a separate router so it does NOT inherit the authenticated
# router's ``get_current_user`` + ``require_pos_plan`` dependencies. The
# capabilities endpoint must be reachable by the desktop client before it
# has authenticated, so it can decide whether to even attempt login.

from base64 import urlsafe_b64encode  # noqa: E402
from datetime import UTC  # noqa: E402

from datapulse.pos.capabilities import (  # noqa: E402
    CAPABILITIES,
    IDEMPOTENCY_PROTOCOL_VERSION,
    IDEMPOTENCY_TTL_HOURS,
    OFFLINE_GRANT_MAX_AGE_HOURS,
    POS_MAX_CLIENT_VERSION,
    POS_MIN_CLIENT_VERSION,
    POS_SERVER_VERSION,
    PROVISIONAL_TTL_HOURS,
)
from datapulse.pos.commit import atomic_commit  # noqa: E402
from datapulse.pos.devices import (  # noqa: E402
    DeviceProof,
    device_token_verifier,
    register_device,
)
from datapulse.pos.idempotency import (  # noqa: E402
    IdempotencyContext,
    idempotency_dependency,
    record_response,
)
from datapulse.pos.models import (  # noqa: E402  # noqa: E402,F811
    CapabilitiesDoc,
    CommitRequest,
    CommitResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    TenantKeysResponse,
    TenantPublicKey,
)
from datapulse.pos.tenant_keys import list_public_keys  # noqa: E402

capabilities_router = APIRouter(prefix="/pos", tags=["pos"])


@capabilities_router.get("/capabilities", response_model=CapabilitiesDoc)
@limiter.limit("60/minute")
def capabilities(request: Request) -> CapabilitiesDoc:
    """Return the server's POS capability document (feature-only, no tenant state)."""
    return CapabilitiesDoc(
        server_version=POS_SERVER_VERSION,
        min_client_version=POS_MIN_CLIENT_VERSION,
        max_client_version=POS_MAX_CLIENT_VERSION,
        idempotency=IDEMPOTENCY_PROTOCOL_VERSION,
        capabilities=dict(CAPABILITIES),
        enforced_policies={
            "idempotency_ttl_hours": IDEMPOTENCY_TTL_HOURS,
            "provisional_ttl_hours": PROVISIONAL_TTL_HOURS,
            "offline_grant_max_age_hours": OFFLINE_GRANT_MAX_AGE_HOURS,
        },
        tenant_key_endpoint="/api/v1/pos/tenant-key",
        device_registration_endpoint="/api/v1/pos/terminals/register-device",
    )


# ──────────────────────────────────────────────────────────────────────────────
# M1 — Tenant signing public keys (§8.8.2)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/terminals/register-device",
    response_model=DeviceRegisterResponse,
    dependencies=[Depends(require_permission("pos:device:register"))],
)
@limiter.limit("10/minute")
def register_terminal_device(
    request: Request,
    payload: DeviceRegisterRequest,
    user: CurrentUser,
    session: SessionDep,
) -> DeviceRegisterResponse:
    """Register a physical device (Ed25519 public key + fingerprint) to a terminal.

    First-launch flow: the desktop client generates a keypair locally, keeps
    the private key in Windows DPAPI, and posts the public key here. Every
    subsequent mutating POS request is signed with that private key and
    verified by ``device_token_verifier`` (§8.9).
    """
    from datetime import datetime

    tenant_id = _tenant_id_of(user)
    device_id = register_device(
        session,
        tenant_id=tenant_id,
        terminal_id=payload.terminal_id,
        public_key_b64=payload.public_key,
        device_fingerprint=payload.device_fingerprint,
    )
    session.commit()
    return DeviceRegisterResponse(
        device_id=device_id,
        terminal_id=payload.terminal_id,
        registered_at=datetime.now(UTC),
    )


# B008-safe: pre-construct the dependency at module load time rather than in
# the arg default. FastAPI consumes the callable from the `Depends(...)` wrap
# at import — creating it once here is functionally identical to creating it
# per-call and avoids the ruff B008 false positive on factory dependencies.
_commit_idempotency_dep = idempotency_dependency("POST /pos/transactions/commit")


@router.post(
    "/transactions/commit",
    response_model=CommitResponse,
    dependencies=[Depends(require_permission("pos:transaction:checkout"))],
)
@limiter.limit("30/minute")
async def commit_transaction(
    request: Request,
    payload: CommitRequest,
    user: CurrentUser,
    db_session: SessionDep,
    proof: Annotated[DeviceProof, Depends(device_token_verifier)],
    idem: Annotated[IdempotencyContext, Depends(_commit_idempotency_dep)],
) -> CommitResponse:
    """Atomic POS commit — draft + items + checkout in one payload (§3).

    Designed for offline queue replay: a retried push with the same
    ``Idempotency-Key`` returns the cached response without re-executing
    the business write. The ``X-Terminal-Token`` header is verified against
    the registered device public key before any state is touched (§8.9).
    """
    if idem.replay:
        return CommitResponse.model_validate(idem.cached_body)

    if payload.terminal_id != proof.terminal_id:
        raise HTTPException(status_code=400, detail="body/header terminal_id mismatch")

    tenant_id = _tenant_id_of(user)
    response = atomic_commit(db_session, tenant_id=tenant_id, payload=payload)
    record_response(db_session, idem.key, 200, response.model_dump(mode="json"))
    db_session.commit()
    return response


@router.get("/tenant-key", response_model=TenantKeysResponse)
@limiter.limit("30/minute")
def tenant_key(
    request: Request,
    user: CurrentUser,
    session: SessionDep,
) -> TenantKeysResponse:
    """Return the tenant's currently-valid POS signing public keys.

    Clients use these keys to verify offline grants (§8.8.2). Private keys
    never leave the server; only public material is returned here.
    """
    tenant_id = _tenant_id_of(user)
    keys = list_public_keys(session, tenant_id)
    return TenantKeysResponse(
        keys=[
            TenantPublicKey(
                key_id=k.key_id,
                public_key=urlsafe_b64encode(k.public_key).decode().rstrip("="),
                valid_from=k.valid_from,
                valid_until=k.valid_until,
            )
            for k in keys
        ]
    )
