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
        "device_fingerprint_v2": "sha256v2:" + "e" * 64,
        "revoked_at": None,
    }
    session.execute.return_value.mappings.return_value.first.return_value = row
    d = load_active_device(session, 7, 1)
    assert isinstance(d, TerminalDevice)
    assert d.id == 3
    assert d.device_fingerprint_v2 == "sha256v2:" + "e" * 64


def test_load_active_device_returns_none_when_absent() -> None:
    from datapulse.pos.devices import load_active_device

    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    assert load_active_device(session, 99, 1) is None


# ─── #480: fingerprint v2 + deprecation window ─────────────────────────────


def test_register_device_stores_v2_fingerprint_when_provided() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    select_res = MagicMock()
    select_res.first.return_value = None
    insert_res = MagicMock()
    insert_res.first.return_value = (101,)
    session.execute.side_effect = [select_res, insert_res]

    _, pk = _fresh_keypair()
    register_device(
        session,
        tenant_id=1,
        terminal_id=7,
        public_key_b64=_b64(pk),
        device_fingerprint="sha256:" + "a" * 64,
        device_fingerprint_v2="sha256v2:" + "f" * 64,
    )

    # Confirm the INSERT received the v2 digest as the `fp2` bind param.
    insert_call = session.execute.call_args_list[1]
    bind = insert_call.args[1]
    assert bind["fp2"] == "sha256v2:" + "f" * 64


def test_register_device_allows_null_v2_for_legacy_clients() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    select_res = MagicMock()
    select_res.first.return_value = None
    insert_res = MagicMock()
    insert_res.first.return_value = (102,)
    session.execute.side_effect = [select_res, insert_res]

    _, pk = _fresh_keypair()
    device_id = register_device(
        session,
        tenant_id=1,
        terminal_id=8,
        public_key_b64=_b64(pk),
        device_fingerprint="sha256:" + "a" * 64,
    )
    assert device_id == 102
    insert_call = session.execute.call_args_list[1]
    assert insert_call.args[1]["fp2"] is None


def test_register_device_400_when_v2_fingerprint_malformed() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    _, pk = _fresh_keypair()
    with pytest.raises(HTTPException) as exc:
        register_device(
            session,
            tenant_id=1,
            terminal_id=7,
            public_key_b64=_b64(pk),
            device_fingerprint="sha256:" + "a" * 64,
            device_fingerprint_v2="not-a-v2-digest",
        )
    assert exc.value.status_code == 400
    assert "sha256v2" in exc.value.detail


def test_register_device_400_when_v1_fingerprint_malformed() -> None:
    from datapulse.pos.devices import register_device

    session = MagicMock()
    _, pk = _fresh_keypair()
    with pytest.raises(HTTPException) as exc:
        register_device(
            session,
            tenant_id=1,
            terminal_id=7,
            public_key_b64=_b64(pk),
            device_fingerprint="not-a-sha256",
        )
    assert exc.value.status_code == 400


def test_is_v1_deprecated_for_tenant_false_when_null() -> None:
    from datapulse.pos.devices import is_v1_deprecated_for_tenant

    session = MagicMock()
    session.execute.return_value.first.return_value = (None,)
    assert is_v1_deprecated_for_tenant(session, tenant_id=1) is False


def test_is_v1_deprecated_for_tenant_false_when_cutoff_future() -> None:
    from datetime import UTC, datetime, timedelta

    from datapulse.pos.devices import is_v1_deprecated_for_tenant

    session = MagicMock()
    future = datetime.now(UTC) + timedelta(days=30)
    session.execute.return_value.first.return_value = (future,)
    assert is_v1_deprecated_for_tenant(session, tenant_id=1) is False


def test_is_v1_deprecated_for_tenant_true_when_cutoff_past() -> None:
    from datetime import UTC, datetime, timedelta

    from datapulse.pos.devices import is_v1_deprecated_for_tenant

    session = MagicMock()
    past = datetime.now(UTC) - timedelta(days=1)
    session.execute.return_value.first.return_value = (past,)
    assert is_v1_deprecated_for_tenant(session, tenant_id=1) is True


def test_is_v1_deprecated_treats_naive_timestamps_as_utc() -> None:
    from datetime import datetime, timedelta

    from datapulse.pos.devices import is_v1_deprecated_for_tenant

    session = MagicMock()
    naive_past = datetime.utcnow() - timedelta(days=1)  # noqa: DTZ003
    session.execute.return_value.first.return_value = (naive_past,)
    assert is_v1_deprecated_for_tenant(session, tenant_id=1) is True


def test_is_v1_deprecated_for_tenant_missing_row_returns_false() -> None:
    from datapulse.pos.devices import is_v1_deprecated_for_tenant

    session = MagicMock()
    session.execute.return_value.first.return_value = None
    assert is_v1_deprecated_for_tenant(session, tenant_id=999) is False
