"""POS offline grant refresh and controlled-substance verification routes.

Also houses the unauthenticated capabilities router (M1 §6.6).

Sub-router for ``pos.py`` facade (issue #543).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, ConfigDict, Field

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    SessionDep,
    _staff_id_of,
    _tenant_id_of,
)
from datapulse.pos.capabilities import (
    CAPABILITIES,
    IDEMPOTENCY_PROTOCOL_VERSION,
    IDEMPOTENCY_TTL_HOURS,
    OFFLINE_GRANT_MAX_AGE_HOURS,
    POS_MAX_CLIENT_VERSION,
    POS_MIN_CLIENT_VERSION,
    POS_SERVER_VERSION,
    PROVISIONAL_TTL_HOURS,
)
from datapulse.pos.models import (
    CapabilitiesDoc,
    OfflineGrantEnvelope,
    PharmacistVerifyRequest,
    PharmacistVerifyResponse,
)
from datapulse.rbac.dependencies import require_permission

router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# M1 — Capabilities (§6.6) — feature-only, unauthenticated
# ──────────────────────────────────────────────────────────────────────────────
#
# Registered as a separate router so it does NOT inherit the authenticated
# router's ``get_current_user`` + ``require_pos_plan`` dependencies. The
# capabilities endpoint must be reachable by the desktop client before it
# has authenticated, so it can decide whether to even attempt login.

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
        update_policy_endpoint="/api/v1/pos/updates/policy",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Refresh offline grant (§8.8 — called by terminal when it regains network to
# extend its offline TTL without reopening the shift).
# ──────────────────────────────────────────────────────────────────────────────


class RefreshGrantRequest(BaseModel):
    """Body for POST /pos/shifts/{shift_id}/refresh-grant."""

    model_config = ConfigDict(frozen=True)

    device_fingerprint: Annotated[str, Field(min_length=16, max_length=200)]
    offline_ttl_hours: Annotated[int, Field(ge=1, le=72)] = 12


@router.post(
    "/shifts/{shift_id}/refresh-grant",
    response_model=OfflineGrantEnvelope,
)
@limiter.limit("30/minute")
def refresh_grant(
    request: Request,
    shift_id: Annotated[int, Path(ge=1)],
    body: RefreshGrantRequest,
    service: ServiceDep,
    db_session: SessionDep,
    user: CurrentUser,
) -> OfflineGrantEnvelope:
    """Mint a fresh offline grant for an existing open shift.

    The terminal calls this when it regains connectivity (e.g. after a half-day
    offline session) so its local grant doesn't expire. Fails with 404 if the
    shift doesn't exist or belongs to another tenant; 409 if the shift is
    already closed.
    """
    from datapulse.pos.grants import issue_grant_for_shift

    tenant_id = _tenant_id_of(user)
    staff_id = _staff_id_of(user)
    shift = service.get_shift_by_id(shift_id, tenant_id=tenant_id)
    if shift is None or int(shift.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail=f"Shift {shift_id} not found")
    if shift.closed_at is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Shift {shift_id} is already closed — grants cannot be refreshed",
        )

    envelope = issue_grant_for_shift(
        db_session,
        tenant_id=tenant_id,
        terminal_id=int(shift.terminal_id),
        shift_id=shift_id,
        staff_id=staff_id,
        device_fingerprint=body.device_fingerprint,
        offline_ttl_hours=body.offline_ttl_hours,
    )
    return envelope


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
