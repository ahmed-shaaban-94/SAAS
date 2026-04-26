"""POS API facade — routes composed from resource sub-routers (see issue #543).

Mounted at ``/api/v1/pos`` and gated by the ``feature_platform`` setting flag.
All endpoints require an authenticated user (RLS handles tenant isolation).

Sub-router files (leading ``_`` = internal to this facade):
  _pos_terminals.py      — open / list / get / pause / resume / close terminal
  _pos_transactions.py   — create / get / list txn + items + checkout + commit
  _pos_catalog.py        — product search / stock info / catalog sync
  _pos_receipts.py       — PDF / thermal / email receipts (B4)
  _pos_void_returns.py   — void + returns (B6a)
  _pos_shifts.py         — shifts + cash drawer events (B6a)
  _pos_offline.py        — offline grant refresh + pharmacist verify + capabilities_router
  _pos_updates.py        — desktop staged update rollout policy

Two handlers remain in this file (register_terminal_device, tenant_key) because
tests monkeypatch ``datapulse.api.routes.pos.register_device`` and
``datapulse.api.routes.pos.list_public_keys`` at module level; those names must
resolve in this module's __dict__ for the patch to take effect.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.api.routes import (
    _pos_catalog,
    _pos_clinical,
    _pos_customer_lookup,
    _pos_delivery,
    _pos_offline,
    _pos_receipts,
    _pos_routes_deps,
    _pos_shifts,
    _pos_terminals,
    _pos_transactions,
    _pos_updates,
    _pos_void_returns,
)
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    SessionDep,
    _tenant_id_of,
)
from datapulse.billing.pos_guard import require_pos_plan
from datapulse.logging import get_logger
from datapulse.pos.devices import register_device
from datapulse.pos.models import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    TenantKeysResponse,
    TenantPublicKey,
)
from datapulse.pos.tenant_keys import list_public_keys
from datapulse.rbac.dependencies import require_permission

log = get_logger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["pos"],
    # B7: billing guard enforces platform/enterprise plan; auth guard requires JWT.
    dependencies=[Depends(get_current_user), Depends(require_pos_plan())],
)

# Re-exports for backwards-compatible test monkeypatching
_legacy_checkout_idempotency_dep = _pos_routes_deps._legacy_checkout_idempotency_dep
_commit_idempotency_dep = _pos_routes_deps._commit_idempotency_dep
_void_idempotency_dep = _pos_routes_deps._void_idempotency_dep
_return_idempotency_dep = _pos_routes_deps._return_idempotency_dep
_shift_close_idempotency_dep = _pos_routes_deps._shift_close_idempotency_dep
_terminal_close_idempotency_dep = _pos_routes_deps._terminal_close_idempotency_dep
_add_item_idempotency_dep = _pos_routes_deps._add_item_idempotency_dep
_update_item_idempotency_dep = _pos_routes_deps._update_item_idempotency_dep
_remove_item_idempotency_dep = _pos_routes_deps._remove_item_idempotency_dep

# Re-export capabilities_router so bootstrap/routers.py can mount it as
# ``pos_routes.capabilities_router`` without modification.
capabilities_router = _pos_offline.capabilities_router

# Compose sub-routers — order matters: FastAPI matches literal paths before
# dynamic ones within a router, but across include_router calls the first
# registered path wins, so terminals must come before transactions.
for _sub in (
    _pos_terminals,
    _pos_transactions,
    _pos_catalog,
    _pos_clinical,
    _pos_customer_lookup,
    _pos_receipts,
    _pos_void_returns,
    _pos_shifts,
    _pos_offline,
    _pos_delivery,
    _pos_updates,
):
    router.include_router(_sub.router)


# ──────────────────────────────────────────────────────────────────────────────
# M1 — Tenant signing public keys (§8.8.2)
#
# Kept in pos.py (not _pos_terminals.py) because test_pos_tenant_key_route.py
# monkeypatches ``datapulse.api.routes.pos.list_public_keys`` at module level.
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
    tenant_id = _tenant_id_of(user)
    device_id = register_device(
        session,
        tenant_id=tenant_id,
        terminal_id=payload.terminal_id,
        public_key_b64=payload.public_key,
        device_fingerprint=payload.device_fingerprint,
        device_fingerprint_v2=payload.device_fingerprint_v2,
    )
    session.commit()
    return DeviceRegisterResponse(
        device_id=device_id,
        terminal_id=payload.terminal_id,
        registered_at=datetime.now(UTC),
    )


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
