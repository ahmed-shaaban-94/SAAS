"""Grant issuance unit tests — pure mocks + signature verification."""

from __future__ import annotations

from base64 import urlsafe_b64decode
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

pytestmark = pytest.mark.unit


def _fake_tenant_key():
    from datapulse.pos.tenant_keys import TenantKey

    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    pub = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    now = datetime.now(timezone.utc)
    return TenantKey("kid-1", 1, priv, pub, now, now + timedelta(days=1)), pub


def test_issue_grant_produces_verifiable_ed25519_signature() -> None:
    from datapulse.pos.grants import issue_grant_for_shift

    fake, pub = _fake_tenant_key()
    session = MagicMock()

    with patch("datapulse.pos.grants.active_private_key", return_value=fake):
        env = issue_grant_for_shift(
            session,
            tenant_id=1,
            terminal_id=5,
            shift_id=9,
            staff_id="s-1",
            device_fingerprint="sha256:" + "a" * 64,
            override_code_count=3,
        )

    assert env.key_id == "kid-1"
    assert len(env.payload.override_codes) == 3
    for c in env.payload.override_codes:
        assert c.code_id and c.salt and c.hash

    sig = urlsafe_b64decode(env.signature_ed25519 + "==")
    msg = env.payload.model_dump_json().encode()
    Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg)  # raises on failure


def test_issue_grant_persists_code_ids_to_grants_issued() -> None:
    from datapulse.pos.grants import issue_grant_for_shift

    fake, _ = _fake_tenant_key()
    session = MagicMock()

    with patch("datapulse.pos.grants.active_private_key", return_value=fake):
        env = issue_grant_for_shift(
            session,
            tenant_id=1,
            terminal_id=5,
            shift_id=9,
            staff_id="s-1",
            device_fingerprint="sha256:" + "a" * 64,
            override_code_count=2,
        )

    # Verify the INSERT call carries the same code_ids as the envelope
    insert_call = session.execute.call_args
    params = insert_call.args[1]
    code_ids = [c.code_id for c in env.payload.override_codes]
    import json as _json

    assert _json.loads(params["codes"]) == code_ids


def test_issue_grant_with_plaintexts_returns_plaintext_map() -> None:
    from datapulse.pos.grants import issue_grant_for_shift_with_plaintexts

    fake, _ = _fake_tenant_key()
    session = MagicMock()

    with patch("datapulse.pos.grants.active_private_key", return_value=fake):
        env, plain = issue_grant_for_shift_with_plaintexts(
            session,
            tenant_id=1,
            terminal_id=5,
            shift_id=9,
            staff_id="s-1",
            device_fingerprint="sha256:" + "a" * 64,
            override_code_count=3,
        )

    assert set(plain) == {c.code_id for c in env.payload.override_codes}
    for code_id, plaintext in plain.items():
        assert len(plaintext) == 8  # OVERRIDE_CODE_LENGTH


def test_override_codes_hash_matches_scrypt_of_plaintext() -> None:
    from base64 import urlsafe_b64decode

    from datapulse.pos.grants import _hash_code, issue_grant_for_shift_with_plaintexts

    fake, _ = _fake_tenant_key()
    session = MagicMock()

    with patch("datapulse.pos.grants.active_private_key", return_value=fake):
        env, plain = issue_grant_for_shift_with_plaintexts(
            session,
            tenant_id=1,
            terminal_id=5,
            shift_id=9,
            staff_id="s-1",
            device_fingerprint="sha256:" + "a" * 64,
            override_code_count=2,
        )

    for code in env.payload.override_codes:
        salt = urlsafe_b64decode(code.salt + "==")
        expected = urlsafe_b64decode(code.hash + "==")
        assert _hash_code(plain[code.code_id], salt) == expected
