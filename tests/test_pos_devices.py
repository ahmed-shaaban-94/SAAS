"""Device module unit tests — pure mocks, no real DB."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def _fresh_keypair() -> tuple[Ed25519PrivateKey, bytes]:
    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    return sk, pk


def _b64(b: bytes) -> str:
    return urlsafe_b64encode(b).decode().rstrip("=")


def test_register_device_inserts_new_row() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    # SELECT existing: None ; INSERT RETURNING id: (42,)
    select_res = MagicMock()
    select_res.first.return_value = None
    insert_res = MagicMock()
    insert_res.first.return_value = (42,)
    session.execute.side_effect = [select_res, insert_res]

    _, pk = _fresh_keypair()
    device_id = register_device(
        session,
        tenant_id=1,
        terminal_id=7,
        public_key_b64=_b64(pk),
        device_fingerprint="sha256:" + "a" * 64,
    )
    assert device_id == 42
    assert session.execute.call_count == 2


def test_register_device_409_when_already_registered() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    session.execute.return_value.first.return_value = (1,)

    _, pk = _fresh_keypair()
    with pytest.raises(HTTPException) as exc:
        register_device(
            session,
            tenant_id=1,
            terminal_id=7,
            public_key_b64=_b64(pk),
            device_fingerprint="sha256:" + "b" * 64,
        )
    assert exc.value.status_code == 409


def test_register_device_400_when_key_wrong_length() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        register_device(
            session,
            tenant_id=1,
            terminal_id=7,
            public_key_b64=_b64(b"tooshort"),
            device_fingerprint="sha256:" + "c" * 64,
        )
    assert exc.value.status_code == 400


def test_verify_signature_accepts_valid_and_rejects_tampered() -> None:
    from datapulse.pos.devices import verify_signature

    sk, pk = _fresh_keypair()
    msg = b"payload"
    sig = sk.sign(msg)
    assert verify_signature(pk, msg, sig) is True
    assert verify_signature(pk, b"tampered", sig) is False


def test_load_active_device_returns_dataclass() -> None:
    from datapulse.pos.devices import TerminalDevice, load_active_device

    session = MagicMock()
    row = {
        "id": 3,
        "tenant_id": 1,
        "terminal_id": 7,
        "public_key": b"x" * 32,
        "device_fingerprint": "sha256:" + "d" * 64,
        "revoked_at": None,
    }
    session.execute.return_value.mappings.return_value.first.return_value = row
    d = load_active_device(session, 7, 1)
    assert isinstance(d, TerminalDevice)
    assert d.id == 3


def test_load_active_device_returns_none_when_absent() -> None:
    from datapulse.pos.devices import load_active_device

    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    assert load_active_device(session, 99, 1) is None
