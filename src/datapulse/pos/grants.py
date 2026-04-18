"""Offline grant issuance for POS terminals.

When a shift opens online, the server mints an ``OfflineGrantEnvelope``:
an Ed25519-signed payload describing what the cashier is allowed to do
while offline, plus a short list of one-time override codes (stored
client-side as salt+scrypt-hash). The server holds the only signing key;
clients verify with the matching public key.

Plaintext override codes are NOT returned in the envelope — supervisors
receive them via an out-of-band channel (admin UI, push notification).
M1 keeps plaintexts ephemeral (in-memory during grant issuance) and does
not persist them server-side; §14.2 hardening backlog proposes AEAD-sealed
plaintext proof when the product matures toward regulated markets.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §8.8.
"""

from __future__ import annotations

import json
import secrets
import uuid
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import scrypt as _scrypt

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.pos.models import (
    OfflineGrantEnvelope,
    OfflineGrantPayload,
    OverrideCodeEntry,
    RoleSnapshot,
)
from datapulse.pos.tenant_keys import active_private_key

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 32

OVERRIDE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # excludes ambiguous chars
OVERRIDE_CODE_LENGTH = 8


def _hash_code(plaintext: str, salt: bytes) -> bytes:
    return _scrypt(
        plaintext.encode(),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_LEN,
    )


def _generate_code() -> str:
    return "".join(secrets.choice(OVERRIDE_CODE_ALPHABET) for _ in range(OVERRIDE_CODE_LENGTH))


def issue_grant_for_shift(
    session: Session,
    *,
    tenant_id: int,
    terminal_id: int,
    shift_id: int,
    staff_id: str,
    device_fingerprint: str,
    role_snapshot_overrides: dict | None = None,
    offline_ttl_hours: int = 12,
    override_code_count: int = 5,
) -> OfflineGrantEnvelope:
    """Mint + persist a fresh offline grant; return the signed envelope.

    Plaintext override codes are generated but NOT included in the envelope.
    Callers that need to distribute plaintexts to supervisors (admin flow)
    should use ``issue_grant_for_shift_with_plaintexts`` instead.
    """
    env, _plain = issue_grant_for_shift_with_plaintexts(
        session,
        tenant_id=tenant_id,
        terminal_id=terminal_id,
        shift_id=shift_id,
        staff_id=staff_id,
        device_fingerprint=device_fingerprint,
        role_snapshot_overrides=role_snapshot_overrides,
        offline_ttl_hours=offline_ttl_hours,
        override_code_count=override_code_count,
    )
    return env


def issue_grant_for_shift_with_plaintexts(
    session: Session,
    *,
    tenant_id: int,
    terminal_id: int,
    shift_id: int,
    staff_id: str,
    device_fingerprint: str,
    role_snapshot_overrides: dict | None = None,
    offline_ttl_hours: int = 12,
    override_code_count: int = 5,
) -> tuple[OfflineGrantEnvelope, dict[str, str]]:
    """Mint a grant + return plaintext override codes for out-of-band distribution.

    Returns ``(envelope, plaintexts_by_code_id)``. Callers MUST transmit
    plaintexts to supervisors through an authenticated channel and MUST NOT
    persist them.
    """
    now = datetime.now(UTC)
    grant_id = str(uuid.uuid4())
    role = RoleSnapshot(**(role_snapshot_overrides or {}))

    codes: list[OverrideCodeEntry] = []
    plaintexts: dict[str, str] = {}
    for i in range(override_code_count):
        code_id = f"c-{i + 1:02d}"
        plain = _generate_code()
        salt = secrets.token_bytes(16)
        digest = _hash_code(plain, salt)
        codes.append(
            OverrideCodeEntry(
                code_id=code_id,
                salt=urlsafe_b64encode(salt).decode().rstrip("="),
                hash=urlsafe_b64encode(digest).decode().rstrip("="),
            )
        )
        plaintexts[code_id] = plain

    payload = OfflineGrantPayload(
        grant_id=grant_id,
        terminal_id=terminal_id,
        tenant_id=tenant_id,
        device_fingerprint=device_fingerprint,
        staff_id=staff_id,
        shift_id=shift_id,
        issued_at=now,
        offline_expires_at=now + timedelta(hours=offline_ttl_hours),
        role_snapshot=role,
        override_codes=codes,
    )

    tkey = active_private_key(session, tenant_id)
    sk = Ed25519PrivateKey.from_private_bytes(tkey.private_key)
    signature = sk.sign(payload.model_dump_json().encode())

    envelope = OfflineGrantEnvelope(
        payload=payload,
        signature_ed25519=urlsafe_b64encode(signature).decode().rstrip("="),
        key_id=tkey.key_id,
    )

    session.execute(
        text(
            """
            INSERT INTO pos.grants_issued
                (grant_id, tenant_id, terminal_id, shift_id, staff_id,
                 key_id, code_ids, issued_at, offline_expires_at)
            VALUES
                (:gid, :tid, :term, :shift, :staff, :kid, :codes, :iss, :exp)
            """
        ),
        {
            "gid": grant_id,
            "tid": tenant_id,
            "term": terminal_id,
            "shift": shift_id,
            "staff": staff_id,
            "kid": tkey.key_id,
            "codes": json.dumps([c.code_id for c in codes]),
            "iss": now,
            "exp": payload.offline_expires_at,
        },
    )
    return envelope, plaintexts
