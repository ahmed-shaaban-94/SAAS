"""Per-tenant Ed25519 signing keypairs for POS offline grants.

Grants are signed with the tenant's private key on the server side; clients
verify with the matching public key fetched via ``GET /pos/tenant-key``.
Private keys never leave the server.

Keys rotate daily. Each key stays valid for verification for
``KEY_ROTATION_INTERVAL + KEY_OVERLAP_WINDOW`` so clients on brief offline
stints can still verify grants signed before the last rotation.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §8.8.2.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

KEY_ROTATION_INTERVAL = timedelta(days=1)
KEY_OVERLAP_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class TenantKey:
    """A tenant's Ed25519 keypair + its validity window."""

    key_id: str
    tenant_id: int
    private_key: bytes  # raw 32-byte Ed25519 private scalar
    public_key: bytes  # raw 32-byte Ed25519 public key
    valid_from: datetime
    valid_until: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def rotate_tenant_key(session: Session, tenant_id: int) -> TenantKey:
    """Generate + persist a fresh keypair for ``tenant_id``.

    Previous keys remain valid for ``KEY_OVERLAP_WINDOW`` past their original
    ``valid_until`` so clients can keep verifying recently-minted grants.
    """
    key_id = str(uuid.uuid4())
    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    pub = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    valid_from = _now()
    valid_until = valid_from + KEY_ROTATION_INTERVAL + KEY_OVERLAP_WINDOW

    session.execute(
        text(
            """
            INSERT INTO pos.tenant_keys
                (key_id, tenant_id, private_key, public_key, valid_from, valid_until)
            VALUES (:kid, :tid, :priv, :pub, :vf, :vu)
            """
        ),
        {
            "kid": key_id,
            "tid": tenant_id,
            "priv": priv,
            "pub": pub,
            "vf": valid_from,
            "vu": valid_until,
        },
    )
    return TenantKey(key_id, tenant_id, priv, pub, valid_from, valid_until)


def active_private_key(session: Session, tenant_id: int) -> TenantKey:
    """Return the most recent non-revoked key for signing new grants.

    If the tenant has no current key, mints a fresh one.
    """
    row = (
        session.execute(
            text(
                """
            SELECT key_id, tenant_id, private_key, public_key, valid_from, valid_until
              FROM pos.tenant_keys
             WHERE tenant_id = :tid
               AND revoked_at IS NULL
               AND valid_until > :now
          ORDER BY valid_from DESC
             LIMIT 1
            """
            ),
            {"tid": tenant_id, "now": _now()},
        )
        .mappings()
        .first()
    )
    if not row:
        return rotate_tenant_key(session, tenant_id)
    return TenantKey(**row)


def list_public_keys(session: Session, tenant_id: int) -> list[TenantKey]:
    """Return all currently-valid keys (for client verification).

    Includes each key's private_key — callers that only need public material
    should read ``.public_key`` and discard the rest. The struct is reused to
    avoid two data classes.
    """
    rows = (
        session.execute(
            text(
                """
            SELECT key_id, tenant_id, private_key, public_key, valid_from, valid_until
              FROM pos.tenant_keys
             WHERE tenant_id = :tid
               AND revoked_at IS NULL
               AND valid_until > :now
          ORDER BY valid_from DESC
            """
            ),
            {"tid": tenant_id, "now": _now()},
        )
        .mappings()
        .all()
    )
    return [TenantKey(**r) for r in rows]
