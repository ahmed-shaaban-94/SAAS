"""POS terminal session routes (open / list / get / pause / resume / close).

Sub-router for ``pos.py`` facade (issue #543).
Does NOT include ``register_terminal_device`` — that handler stays in the facade
because tests monkeypatch ``datapulse.api.routes.pos.register_device`` directly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy import text

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    SessionDep,
    _staff_id_of,
    _tenant_id_of,
    _terminal_close_idempotency_dep,
)
from datapulse.pos.exceptions import PosError
from datapulse.pos.idempotency import (
    IdempotencyContext,
    raise_for_replayed_error,
    record_idempotent_exception,
    record_idempotent_success,
)
from datapulse.pos.models import (
    TerminalCloseRequest,
    TerminalOpenRequest,
    TerminalSessionResponse,
)
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


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
) -> TerminalSessionResponse:
    """Open a fresh POS terminal session (cashier shift).

    §1.4 single-terminal enforcement is delivered by three other layers
    (client guard via GET /terminals/active-for-me, device-bound per-request
    Ed25519 proof via device_token_verifier, and tenant-level flags in
    bronze.tenants). The server-side guard ON THIS ROUTE belongs in the
    service layer so it can share PosService's existing DB session; moving
    it there is tracked as M2 follow-up work.
    """
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
    tenant_id = _tenant_id_of(user)
    session = service.get_terminal(terminal_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Terminal {terminal_id} not found")
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.post(
    "/terminals/{terminal_id}/pause",
    response_model=TerminalSessionResponse,
    dependencies=[Depends(require_permission("pos:terminal:open"))],
)
@limiter.limit("30/minute")
def pause_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Pause a terminal — operator stepped away; blocks new transactions."""
    tenant_id = _tenant_id_of(user)
    session = service.pause_terminal(terminal_id, tenant_id=tenant_id)
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.post(
    "/terminals/{terminal_id}/resume",
    response_model=TerminalSessionResponse,
    dependencies=[Depends(require_permission("pos:terminal:open"))],
)
@limiter.limit("30/minute")
def resume_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> TerminalSessionResponse:
    """Resume a paused terminal back to ``active`` state."""
    tenant_id = _tenant_id_of(user)
    session = service.resume_terminal(terminal_id, tenant_id=tenant_id)
    return TerminalSessionResponse.model_validate(session.model_dump())


@router.post(
    "/terminals/{terminal_id}/close",
    response_model=TerminalSessionResponse,
    dependencies=[Depends(require_permission("pos:terminal:close"))],
)
@limiter.limit("30/minute")
def close_terminal(
    request: Request,
    terminal_id: Annotated[int, Path(ge=1)],
    body: TerminalCloseRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_terminal_close_idempotency_dep)],
) -> TerminalSessionResponse:
    """Close a terminal — records closing cash and seals the shift.

    Requires ``pos:terminal:close`` (Codex P2): prior code had no RBAC
    on this mutating endpoint, so any authenticated POS user could
    close another cashier's active terminal. The permission is already
    seeded — just was never required by the route.
    """
    if idem.replay:
        raise_for_replayed_error(idem)
        return TerminalSessionResponse.model_validate(idem.cached_body)

    try:
        tenant_id = _tenant_id_of(user)
        session = service.close_terminal(
            terminal_id,
            closing_cash=Decimal(str(body.closing_cash)),
            tenant_id=tenant_id,
        )
    except (HTTPException, PosError) as exc:
        record_idempotent_exception(db_session, idem, exc)
        raise
    result = TerminalSessionResponse.model_validate(session.model_dump())
    record_idempotent_success(db_session, idem, 200, result.model_dump(mode="json"))
    return result
