"""POS capability document — feature-only, unauthenticated.

The ``CapabilitiesDoc`` returned by ``GET /pos/capabilities`` is the contract
the desktop client uses to decide whether it may safely push mutations.
The client refuses to sync against any server that does not advertise
``idempotency: "v1"`` + ``capabilities.idempotency_key_header: true``.

Tenant state (active terminals, multi-terminal flag) lives at
``GET /pos/terminals/active-for-me`` — this document is feature-only.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §6.6.
"""

from __future__ import annotations

POS_SERVER_VERSION: str = "1.0.0"
POS_MIN_CLIENT_VERSION: str = "1.0.0"
POS_MAX_CLIENT_VERSION: str | None = None

IDEMPOTENCY_PROTOCOL_VERSION: str = "v1"
CAPABILITIES_VERSION: str = "v1"

IDEMPOTENCY_TTL_HOURS: int = 168
PROVISIONAL_TTL_HOURS: int = 72
OFFLINE_GRANT_MAX_AGE_HOURS: int = 12

CAPABILITIES: dict[str, bool] = {
    "idempotency_key_header": True,
    "pos_commit_endpoint": True,
    "pos_catalog_stream": False,  # deferred to M2
    "pos_shift_close": True,
    "pos_corrective_void": True,
    "override_reason_header": True,
    "terminal_device_token": True,
    "offline_grant_asymmetric": True,
    "multi_terminal_supported": False,
}
