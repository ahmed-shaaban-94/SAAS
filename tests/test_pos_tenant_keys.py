"""Tenant keypair module — pure unit tests, mocked session only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_rotate_tenant_key_inserts_row_and_returns_keypair() -> None:
    from datapulse.pos.tenant_keys import rotate_tenant_key

    session = MagicMock()
    key = rotate_tenant_key(session, tenant_id=1)

    assert key.key_id
    assert key.tenant_id == 1
    assert len(key.private_key) == 32
    assert len(key.public_key) == 32
    assert key.valid_from < key.valid_until
    # Keypair must validate under Ed25519
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    sk = Ed25519PrivateKey.from_private_bytes(key.private_key)
    msg = b"hello"
    sig = sk.sign(msg)
    sk.public_key().verify(sig, msg)
    session.execute.assert_called_once()


def test_list_public_keys_maps_rows_to_dataclass() -> None:
    from datapulse.pos.tenant_keys import list_public_keys

    session = MagicMock()
    now = datetime.now(UTC)
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "key_id": "k1",
            "tenant_id": 1,
            "private_key": b"x" * 32,
            "public_key": b"y" * 32,
            "valid_from": now,
            "valid_until": now + timedelta(days=1),
        },
        {
            "key_id": "k2",
            "tenant_id": 1,
            "private_key": b"a" * 32,
            "public_key": b"b" * 32,
            "valid_from": now,
            "valid_until": now + timedelta(days=2),
        },
    ]
    keys = list_public_keys(session, 1)
    assert [k.key_id for k in keys] == ["k1", "k2"]


def test_active_private_key_mints_fresh_when_absent() -> None:
    from datapulse.pos.tenant_keys import active_private_key

    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    key = active_private_key(session, tenant_id=9)
    assert key.tenant_id == 9
    assert len(key.private_key) == 32


def test_active_private_key_returns_existing_row() -> None:
    from datapulse.pos.tenant_keys import active_private_key

    session = MagicMock()
    now = datetime.now(UTC)
    session.execute.return_value.mappings.return_value.first.return_value = {
        "key_id": "k-existing",
        "tenant_id": 3,
        "private_key": b"p" * 32,
        "public_key": b"q" * 32,
        "valid_from": now,
        "valid_until": now + timedelta(days=1),
    }
    key = active_private_key(session, tenant_id=3)
    assert key.key_id == "k-existing"
