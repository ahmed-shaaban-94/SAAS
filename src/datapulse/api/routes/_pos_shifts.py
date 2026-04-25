"""POS shift management and cash drawer event routes (B6a).

Sub-router for ``pos.py`` facade (issue #543).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    SessionDep,
    _shift_close_idempotency_dep,
    _staff_id_of,
    _tenant_id_of,
)
from datapulse.pos.idempotency import IdempotencyContext, record_response
from datapulse.pos.models import (
    CashCountRequest,
    CashDrawerEventResponse,
    CloseShiftRequestV2,
    ShiftRecord,
    ShiftSummaryResponse,
    StartShiftRequest,
)
from datapulse.pos.models.commission import ActiveShiftResponse
from datapulse.pos.shift_close_guard import enforce_close_guard
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


@router.post(
    "/shifts",
    response_model=ShiftRecord,
    status_code=201,
    dependencies=[Depends(require_permission("pos:shift:open"))],
)
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


@router.get("/shifts/current", response_model=ActiveShiftResponse)
@limiter.limit("120/minute")
def get_current_shift_for_me(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
) -> ActiveShiftResponse:
    """Return the authenticated staff's active shift + commission + target (#627).

    Terminal status-strip polls this after every sale so the commission pill
    and trophy bar update live. 404 when the staff has no open shift (UI
    shows the "open shift" prompt instead of the status strip).
    """
    shift = service.get_active_shift_for_staff(
        tenant_id=_tenant_id_of(user),
        staff_id=_staff_id_of(user),
    )
    if shift is None:
        raise HTTPException(status_code=404, detail="No active shift for this user")
    return shift


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
    body: CloseShiftRequestV2,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_shift_close_idempotency_dep)],
) -> ShiftSummaryResponse:
    """Close a cashier shift and compute cash reconciliation.

    Returns ``expected_cash``, ``variance`` (closing - expected), transaction count,
    and total sales for the shift.

    Codex P2: ``enforce_close_guard`` runs before delegating to the
    service and rejects the close when any ``pos.transactions`` row for
    this shift still has ``commit_confirmed_at IS NULL`` (provisional /
    unreconciled transactions on disk). The client also supplies its own
    ``local_unresolved`` claim (count + digest) which the guard
    cross-checks against the server-side count. The whole route is
    idempotency-keyed so a network retry replays the cached response
    instead of double-closing.
    """
    if idem.replay:
        if idem.cached_status and idem.cached_status >= 400:
            detail = (idem.cached_body or {}).get("detail", "idempotent request failed")
            raise HTTPException(status_code=idem.cached_status, detail=detail)
        return ShiftSummaryResponse.model_validate(idem.cached_body)

    tenant_id = _tenant_id_of(user)
    shift = service.get_shift_by_id(shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail=f"Shift {shift_id} not found")
    try:
        enforce_close_guard(
            db_session,
            shift_id=shift_id,
            tenant_id=tenant_id,
            terminal_id=shift.terminal_id,
            claim_count=body.local_unresolved.count,
            claim_digest=body.local_unresolved.digest,
        )
    except HTTPException as exc:
        record_response(
            db_session,
            idem.key,
            exc.status_code,
            {"detail": exc.detail},
            tenant_id=idem.tenant_id,
        )
        db_session.commit()
        raise

    result = service.close_shift(
        shift_id=shift_id,
        closing_cash=Decimal(str(body.closing_cash)),
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
    "/terminals/{terminal_id}/cash-events",
    response_model=CashDrawerEventResponse,
    status_code=201,
    dependencies=[Depends(require_permission("pos:cash:event:create"))],
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
