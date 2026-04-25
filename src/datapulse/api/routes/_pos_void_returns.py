"""POS void and returns routes (B6a).

Sub-router for ``pos.py`` facade (issue #543).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    SessionDep,
    _return_idempotency_dep,
    _staff_id_of,
    _tenant_id_of,
    _void_idempotency_dep,
)
from datapulse.pos.idempotency import IdempotencyContext, record_response
from datapulse.pos.models import (
    ReturnDetailResponse,
    ReturnRequest,
    ReturnResponse,
    VoidRequest,
    VoidResponse,
)
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


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
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_void_idempotency_dep)],
) -> VoidResponse:
    """Void a completed transaction — reverses inventory and writes an audit log.

    Restricted to supervisors / managers. Only ``completed`` transactions
    may be voided; draft transactions should be abandoned by removing items.
    """
    if idem.replay:
        return VoidResponse.model_validate(idem.cached_body)

    tenant_id = _tenant_id_of(user)
    result = await service.void_transaction(
        transaction_id=transaction_id,
        tenant_id=tenant_id,
        reason=body.reason,
        voided_by=_staff_id_of(user),
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
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_return_idempotency_dep)],
) -> ReturnResponse:
    """Process a drug return against a completed transaction.

    Creates a return transaction, restocks inventory via FEFO movement,
    and records a ``pos.returns`` audit entry.
    """
    if idem.replay:
        return ReturnResponse.model_validate(idem.cached_body)

    tenant_id = _tenant_id_of(user)
    result = await service.process_return(
        original_transaction_id=body.original_transaction_id,
        tenant_id=tenant_id,
        staff_id=_staff_id_of(user),
        items=list(body.items),
        reason=body.reason,
        refund_method=body.refund_method,
        notes=body.notes,
    )
    record_response(
        db_session,
        idem.key,
        201,
        result.model_dump(mode="json"),
        tenant_id=idem.tenant_id,
    )
    db_session.commit()
    return result


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
