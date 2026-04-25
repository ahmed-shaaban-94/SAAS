"""POS transaction routes (create / get / list / items / checkout / commit).

Sub-router for ``pos.py`` facade (issue #543).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    SessionDep,
    _add_item_idempotency_dep,
    _commit_idempotency_dep,
    _legacy_checkout_idempotency_dep,
    _remove_item_idempotency_dep,
    _staff_id_of,
    _tenant_id_of,
    _update_item_idempotency_dep,
)
from datapulse.pos.commit import atomic_commit
from datapulse.pos.constants import TransactionStatus
from datapulse.pos.devices import DeviceProof, device_token_verifier
from datapulse.pos.idempotency import IdempotencyContext, record_response
from datapulse.pos.models import (
    AddItemRequest,
    CheckoutRequest,
    CheckoutResponse,
    CommitRequest,
    CommitResponse,
    PosCartItem,
    TransactionDetailResponse,
    TransactionResponse,
    UpdateItemRequest,
)
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=201,
    dependencies=[Depends(require_permission("pos:transaction:create"))],
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
    dependencies=[Depends(require_permission("pos:transaction:create"))],
)
@limiter.limit("30/minute")
async def add_item(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: AddItemRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_add_item_idempotency_dep)],
) -> PosCartItem:
    """Add a drug to the active draft transaction (FEFO batch + stock check)."""
    if idem.replay:
        return PosCartItem.model_validate(idem.cached_body)
    txn = service.get_transaction_detail(transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    if txn.status != TransactionStatus.draft:
        raise HTTPException(status_code=409, detail="Only draft transactions can be edited")
    result = await service.add_item(
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
    record_response(db_session, idem.key, 200, result.model_dump(mode="json"))
    db_session.commit()
    return result


@router.patch(
    "/transactions/{transaction_id}/items/{item_id}",
    response_model=PosCartItem,
    dependencies=[Depends(require_permission("pos:transaction:create"))],
)
@limiter.limit("30/minute")
async def update_item(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
    body: UpdateItemRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_update_item_idempotency_dep)],
) -> PosCartItem:
    """Update an existing line item's quantity / price / discount.

    ``override_price=None`` means "leave the persisted unit_price as-is"
    — passing ``Decimal("0")`` here used to zero the line on innocent
    quantity-only PATCHes (Codex P1).
    """
    if idem.replay:
        return PosCartItem.model_validate(idem.cached_body)
    tenant_id = _tenant_id_of(user)
    result = service.update_item(
        item_id,
        transaction_id=transaction_id,
        tenant_id=tenant_id,
        quantity=Decimal(str(body.quantity)),
        unit_price=(Decimal(str(body.override_price)) if body.override_price is not None else None),
        discount=Decimal(str(body.discount)) if body.discount is not None else None,
    )
    record_response(db_session, idem.key, 200, result.model_dump(mode="json"))
    db_session.commit()
    return result


@router.delete(
    "/transactions/{transaction_id}/items/{item_id}",
    status_code=204,
    dependencies=[Depends(require_permission("pos:transaction:create"))],
)
@limiter.limit("30/minute")
async def remove_item(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_remove_item_idempotency_dep)],
) -> Response:
    """Remove a single line item from a draft transaction."""
    if idem.replay:
        return Response(status_code=204)
    tenant_id = _tenant_id_of(user)
    deleted = service.remove_item(item_id, transaction_id=transaction_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    record_response(db_session, idem.key, 204, None)
    db_session.commit()
    return Response(status_code=204)


@router.post(
    "/transactions/{transaction_id}/checkout",
    response_model=CheckoutResponse,
    dependencies=[Depends(require_permission("pos:transaction:checkout"))],
)
@limiter.limit("30/minute")
async def checkout(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: CheckoutRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_legacy_checkout_idempotency_dep)],
) -> CheckoutResponse:
    """Finalise a draft transaction: totals -> payment -> stock -> bronze write.

    Audit C1 hardening: this route now requires an ``Idempotency-Key`` header
    (the client should mint a fresh UUID per user-initiated checkout and
    re-send it on retry) and the ``pos:transaction:checkout`` permission.
    Device-bound Ed25519 verification stays exclusive to the desktop
    ``/transactions/commit`` route — browser pilots have no private keypair.
    """
    if idem.replay:
        return CheckoutResponse.model_validate(idem.cached_body)
    result = await service.checkout(
        transaction_id=transaction_id,
        tenant_id=_tenant_id_of(user),
        request=body,
    )
    record_response(
        db_session,
        idem.key,
        200,
        result.model_dump(mode="json"),
        tenant_id=idem.tenant_id,
    )
    db_session.commit()
    return result


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
    record_response(
        db_session,
        idem.key,
        200,
        response.model_dump(mode="json"),
        tenant_id=idem.tenant_id,
    )
    db_session.commit()
    return response
