"""Shared dependencies and helpers for POS sub-routers (issue #543).

Every ``_pos_*.py`` sub-router imports ``ServiceDep``, ``CurrentUser``,
``SessionDep``, the two tenant/staff helpers, and the module-level
idempotency dep instances from this module.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user  # noqa: E402
from datapulse.api.deps import get_pos_service, get_tenant_session
from datapulse.pos.idempotency import idempotency_dependency
from datapulse.pos.service import PosService

ServiceDep = Annotated[PosService, Depends(get_pos_service)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
SessionDep = Annotated[Session, Depends(get_tenant_session)]

# Audit C1 — the legacy 3-step checkout (draft -> items -> checkout) was missing
# RBAC + idempotency. Declaring at module level so tests can override via
# monkeypatch.setattr("datapulse.api.routes.pos._legacy_checkout_idempotency_dep", ...).
_legacy_checkout_idempotency_dep = idempotency_dependency("POST /pos/transactions/{id}/checkout")

# B008-safe: pre-construct the dependency at module load time rather than in
# the arg default. FastAPI consumes the callable from the `Depends(...)` wrap
# at import — creating it once here is functionally identical to creating it
# per-call and avoids the ruff B008 false positive on factory dependencies.
_commit_idempotency_dep = idempotency_dependency("POST /pos/transactions/commit")
_void_idempotency_dep = idempotency_dependency("POST /pos/transactions/{id}/void")
_return_idempotency_dep = idempotency_dependency("POST /pos/returns")
_shift_close_idempotency_dep = idempotency_dependency("POST /pos/shifts/{id}/close")
_terminal_close_idempotency_dep = idempotency_dependency("POST /pos/terminals/{id}/close")
_add_item_idempotency_dep = idempotency_dependency("POST /pos/transactions/{id}/items")


def _tenant_id_of(user: CurrentUser) -> int:  # type: ignore[valid-type]
    """Coerce the JWT ``tenant_id`` claim to int.

    Auth already rejects missing tenant claims when ``default_tenant_id`` is
    unset; this is a defence-in-depth guard so a misconfigured dev-mode token
    can never silently serve tenant 1 data to a cross-tenant caller.
    """
    tid = user.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=401, detail="Missing tenant context")
    return int(tid)


def _staff_id_of(user: CurrentUser) -> str:  # type: ignore[valid-type]
    """Resolve a staff identifier from the JWT (sub, then email)."""
    return str(user.get("sub") or user.get("email") or "unknown")
