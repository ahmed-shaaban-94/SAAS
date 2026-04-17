"""Device-bound POS terminal credentials.

Every mutating POS request carries an Ed25519 signature made with a private
key stored only on the registered physical machine. The server verifies the
signature against the public key recorded at device-registration time. A
second machine cannot operate an existing terminal even with a valid JWT,
because it lacks the device private key.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §8.9.
"""

from __future__ import annotations

import hashlib
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

CLOCK_SKEW_TOLERANCE_MINUTES: int = 2


@dataclass(frozen=True)
class TerminalDevice:
    """A row from pos.terminal_devices."""

    id: int
    tenant_id: int
    terminal_id: int
    public_key: bytes
    device_fingerprint: str
    revoked_at: datetime | None


@dataclass(frozen=True)
class DeviceProof:
    """Successful per-request device proof (output of device_token_verifier)."""

    terminal_id: int
    device: TerminalDevice
    signed_at: datetime
    idempotency_key: str


def _pad_b64url(s: str) -> bytes:
    """Decode a base64-url string that may be missing padding."""
    return urlsafe_b64decode(s + "=" * (-len(s) % 4))


def register_device(
    session: Session,
    *,
    tenant_id: int,
    terminal_id: int,
    public_key_b64: str,
    device_fingerprint: str,
) -> int:
    """Insert a new device row for ``terminal_id``.

    Raises HTTPException(400) on malformed public key, HTTPException(409) if
    the terminal already has an active (non-revoked) device.
    """
    pk = _pad_b64url(public_key_b64)
    if len(pk) != 32:
        raise HTTPException(status_code=400, detail="public_key must be 32 raw bytes")

    existing = session.execute(
        text(
            """SELECT id FROM pos.terminal_devices
                WHERE terminal_id = :tid AND revoked_at IS NULL"""
        ),
        {"tid": terminal_id},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="terminal already has a registered device")

    row = session.execute(
        text(
            """
            INSERT INTO pos.terminal_devices
                (tenant_id, terminal_id, public_key, device_fingerprint)
            VALUES (:tenant, :tid, :pk, :fp)
            RETURNING id
            """
        ),
        {"tenant": tenant_id, "tid": terminal_id, "pk": pk, "fp": device_fingerprint},
    ).first()
    return int(row[0])


def load_active_device(
    session: Session, terminal_id: int, tenant_id: int
) -> TerminalDevice | None:
    row = session.execute(
        text(
            """
            SELECT id, tenant_id, terminal_id, public_key, device_fingerprint, revoked_at
              FROM pos.terminal_devices
             WHERE terminal_id = :tid
               AND tenant_id   = :tenant
               AND revoked_at IS NULL
            """
        ),
        {"tid": terminal_id, "tenant": tenant_id},
    ).mappings().first()
    return TerminalDevice(**row) if row else None


def verify_signature(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature. Returns False on any failure."""
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False


async def device_token_verifier(
    request: Request,
    x_terminal_id: int = Header(..., alias="X-Terminal-Id"),
    x_device_fingerprint: str = Header(..., alias="X-Device-Fingerprint"),
    x_signed_at: str = Header(..., alias="X-Signed-At"),
    x_terminal_token: str = Header(..., alias="X-Terminal-Token"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> DeviceProof:
    """FastAPI dependency: verify the per-request device-bound Ed25519 proof.

    Reads the session from ``request.state.db_session`` if present (injected
    by tenant-scoped middleware); otherwise resolves ``get_tenant_session``
    lazily. Route handlers typically depend on this via
    ``Depends(device_token_verifier)`` alongside ``get_tenant_session``.

    §8.9.2 canonical digest formula.
    """
    from datapulse.api.deps import get_tenant_session  # local to avoid circular import

    # Resolve session — prefer an already-opened one on request.state
    session: Session | None = getattr(request.state, "db_session", None)
    if session is None:
        session_iter = get_tenant_session()
        session = next(session_iter)  # pragma: no cover — tests provide request.state

    tenant_id = int(getattr(request.state, "tenant_id", 1))

    device = load_active_device(session, x_terminal_id, tenant_id)
    if device is None:
        raise HTTPException(status_code=401, detail="unknown device")
    if device.revoked_at is not None:
        raise HTTPException(status_code=401, detail="device revoked")
    if device.device_fingerprint != x_device_fingerprint:
        raise HTTPException(status_code=401, detail="fingerprint mismatch")

    try:
        signed_at_dt = datetime.fromisoformat(x_signed_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid X-Signed-At") from e

    now = datetime.now(timezone.utc)
    if signed_at_dt > now + timedelta(minutes=CLOCK_SKEW_TOLERANCE_MINUTES):
        raise HTTPException(status_code=401, detail="signed_at in the future")

    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest()
    digest = "\n".join(
        [
            request.method,
            request.url.path,
            idempotency_key,
            str(x_terminal_id),
            body_hash,
            x_signed_at,
        ]
    ).encode()

    signature = _pad_b64url(x_terminal_token)
    if not verify_signature(device.public_key, digest, signature):
        raise HTTPException(status_code=401, detail="signature verification failed")

    return DeviceProof(
        terminal_id=x_terminal_id,
        device=device,
        signed_at=signed_at_dt,
        idempotency_key=idempotency_key,
    )
