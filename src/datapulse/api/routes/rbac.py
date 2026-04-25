"""RBAC routes — manager PIN verification for in-app override flows.

The POS UI invokes ``POST /rbac/verify-pin`` to gate destructive cart
actions (line removal, quantity-zeroing, future zero-price overrides)
behind a manager-presence check. The endpoint validates the typed PIN
against ``public.tenant_members.pharmacist_pin_hash`` for the current
tenant — any active member with a matching peppered HMAC hash is
considered "manager-present" for the purposes of approving the action.

The hash function is shared with the pharmacist controlled-substance
verifier (``datapulse.pos.pharmacist_verifier.hash_pin``) so the same
column doubles as a manager PIN store. Multi-PIN-per-role separation
can be added later without changing this contract.

Returns ``{ "approved": bool }``. Never returns 401/403 on PIN mismatch
— the frontend modal stays open and lets the cashier retry. Auth on
the route itself still requires a valid JWT (otherwise 401).

Tenant isolation
----------------
``_tenant_id_of(user)`` is the JWT-derived tenant. The lookup query
filters ``WHERE tenant_id = :tenant_id`` so a stolen PIN from one
tenant cannot approve actions in another tenant.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import CurrentUser, _tenant_id_of
from datapulse.core.auth import get_tenant_session
from datapulse.pos.pharmacist_verifier import hash_pin

router = APIRouter(prefix="/rbac", tags=["rbac"])


class VerifyPinRequest(BaseModel):
    """Body of ``POST /rbac/verify-pin``."""

    pin: str = Field(min_length=4, max_length=10, description="4-10 digit numeric PIN")


class VerifyPinResponse(BaseModel):
    """Response of ``POST /rbac/verify-pin``."""

    approved: bool


@router.post("/verify-pin", response_model=VerifyPinResponse)
@limiter.limit("10/minute")
def verify_pin(
    request: Request,
    body: VerifyPinRequest,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> VerifyPinResponse:
    """Approve a manager-PIN override for the current tenant.

    Body: ``{"pin": "1234"}``. Returns ``{"approved": true}`` when the
    peppered hash of ``pin`` matches at least one active member's
    ``pharmacist_pin_hash`` in the same tenant; ``{"approved": false}``
    otherwise. A `false` is NOT a 401 — the modal lets the cashier
    retry with a different PIN.

    Rate-limited to 10/min per IP to slow brute-force; combine with the
    front-end's 3-strikes lockout once that lands.
    """
    tenant_id = _tenant_id_of(user)
    pin_hash = hash_pin(body.pin)
    row = (
        session.execute(
            text(
                """
                SELECT 1
                FROM   public.tenant_members
                WHERE  tenant_id           = :tenant_id
                AND    pharmacist_pin_hash = :pin_hash
                AND    is_active           = TRUE
                LIMIT  1
                """,
            ),
            {"tenant_id": tenant_id, "pin_hash": pin_hash},
        )
        .mappings()
        .first()
    )
    return VerifyPinResponse(approved=row is not None)
