"""M1 offline-mode models: capabilities, tenant keys, device registration,
offline grants, and override tokens.

These wire together the Electron POS desktop's trust handshake with the
backend and are defined in ``docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CapabilitiesDoc(BaseModel):
    """Feature-only capability document returned by GET /pos/capabilities."""

    model_config = ConfigDict(frozen=True)

    server_version: str
    min_client_version: str
    max_client_version: str | None
    idempotency: str
    capabilities: dict[str, bool]
    enforced_policies: dict[str, int]
    tenant_key_endpoint: str
    device_registration_endpoint: str


class TenantPublicKey(BaseModel):
    """Public Ed25519 verification key advertised to POS clients."""

    model_config = ConfigDict(frozen=True)

    key_id: str
    public_key: str  # base64-url of raw 32-byte public key
    valid_from: datetime
    valid_until: datetime


class TenantKeysResponse(BaseModel):
    """Response body for GET /pos/tenant-key."""

    model_config = ConfigDict(frozen=True)

    keys: list[TenantPublicKey]


class DeviceRegisterRequest(BaseModel):
    """Request body for POST /pos/devices (device registration, §8.9)."""

    model_config = ConfigDict(frozen=True)

    terminal_id: int = Field(ge=1)
    public_key: str = Field(min_length=32)  # base64-url raw 32-byte ed25519 pubkey
    device_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    # v2 fingerprint is optional: old clients predate #480. New desktop
    # builds always include it when the host is reliably fingerprintable.
    device_fingerprint_v2: str | None = Field(default=None, pattern=r"^sha256v2:[0-9a-f]{64}$")


class DeviceRegisterResponse(BaseModel):
    """Response body for POST /pos/devices."""

    model_config = ConfigDict(frozen=True)

    device_id: int
    terminal_id: int
    registered_at: datetime


class OverrideCodeEntry(BaseModel):
    """One hashed pharmacist/supervisor override code packed into an offline grant."""

    model_config = ConfigDict(frozen=True)

    code_id: str
    salt: str
    hash: str
    issued_to_staff_id: str | None = None


class RoleSnapshot(BaseModel):
    """Capability snapshot baked into an offline grant at issuance."""

    model_config = ConfigDict(frozen=True)

    can_checkout: bool = True
    can_void: bool = False
    can_override_price: bool = False
    can_apply_discount: bool = True
    max_discount_pct: int = 15
    can_process_returns: bool = False
    can_open_drawer_no_sale: bool = False
    can_close_shift: bool = True


class OfflineGrantPayload(BaseModel):
    """Claims body inside a signed offline grant envelope."""

    model_config = ConfigDict(frozen=True)

    iss: str = "datapulse-pos"
    grant_id: str
    terminal_id: int
    tenant_id: int
    device_fingerprint: str
    staff_id: str
    shift_id: int
    issued_at: datetime
    offline_expires_at: datetime
    role_snapshot: RoleSnapshot
    override_codes: list[OverrideCodeEntry]
    capabilities_version: str = "v1"


class OfflineGrantEnvelope(BaseModel):
    """Signed envelope carrying a grant payload + Ed25519 signature."""

    model_config = ConfigDict(frozen=True)

    payload: OfflineGrantPayload
    signature_ed25519: str  # base64-url Ed25519 signature of payload JSON
    key_id: str  # which tenant key minted the signature


class OverrideTokenClaim(BaseModel):
    """Device-signed claim used to consume an override code (§8.8.6)."""

    model_config = ConfigDict(frozen=True)

    grant_id: str
    code_id: str
    tenant_id: int
    terminal_id: int
    shift_id: int
    action: Literal[
        "retry_override",
        "void",
        "no_sale",
        "price_override",
        "discount_above_limit",
    ]
    action_subject_id: str | None = None
    consumed_at: datetime


class OverrideTokenEnvelope(BaseModel):
    """Signed envelope around an ``OverrideTokenClaim``."""

    model_config = ConfigDict(frozen=True)

    claim: OverrideTokenClaim
    signature: str  # base64-url Ed25519 signature of claim JSON, signed by the device key
