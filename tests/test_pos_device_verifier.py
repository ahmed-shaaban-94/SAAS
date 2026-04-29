"""device_token_verifier tests — exercises the #480 v2 + deprecation logic.

These tests build a minimal FastAPI app, override the tenant session
dependency, and stub ``load_active_device`` / ``is_v1_deprecated_for_tenant``
to control the per-request context without a live database.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from datapulse.api.deps import get_tenant_session
from datapulse.core.auth import get_current_user
from datapulse.pos import devices as devices_mod
from datapulse.pos.devices import DeviceProof, TerminalDevice, device_token_verifier

pytestmark = pytest.mark.unit

_FP_V1 = "sha256:" + "a" * 64
_FP_V2 = "sha256v2:" + "b" * 64
_FP_V2_OTHER = "sha256v2:" + "c" * 64


def _b64url(b: bytes) -> str:
    return urlsafe_b64encode(b).decode().rstrip("=")


def _build_signed_headers(
    *,
    sk: Ed25519PrivateKey,
    terminal_id: int,
    v1: str,
    v2: str | None,
    body: bytes,
    signed_at: str,
    idempotency_key: str,
) -> dict[str, str]:
    body_hash = sha256(body).hexdigest()
    canonical = "\n".join(
        [
            "POST",
            "/verify",
            idempotency_key,
            str(terminal_id),
            body_hash,
            signed_at,
        ]
    ).encode()
    sig = sk.sign(canonical)
    headers = {
        "X-Terminal-Id": str(terminal_id),
        "X-Device-Fingerprint": v1,
        "X-Signed-At": signed_at,
        "X-Terminal-Token": _b64url(sig),
        "Idempotency-Key": idempotency_key,
    }
    if v2 is not None:
        headers["X-Device-Fingerprint-V2"] = v2
    return headers


def _make_app(
    device: TerminalDevice | None,
    *,
    v1_deprecated: bool = False,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    monkeypatch.setattr(devices_mod, "load_active_device", lambda *_a, **_k: device)
    monkeypatch.setattr(devices_mod, "is_v1_deprecated_for_tenant", lambda *_a, **_k: v1_deprecated)

    app = FastAPI()
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: {"tenant_id": 1, "roles": ["pos"]}

    @app.middleware("http")
    async def _inject_tenant(request, call_next):
        request.state.tenant_id = 1
        return await call_next(request)

    @app.post("/verify")
    async def _verify(proof: DeviceProof = Depends(device_token_verifier)):  # noqa: B008
        return {
            "terminal_id": proof.terminal_id,
            "idempotency_key": proof.idempotency_key,
        }

    return app


def _fresh_device(*, v2: str | None = _FP_V2) -> tuple[Ed25519PrivateKey, TerminalDevice]:
    sk = Ed25519PrivateKey.generate()
    pk_bytes = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    device = TerminalDevice(
        id=1,
        tenant_id=1,
        terminal_id=5,
        public_key=pk_bytes,
        device_fingerprint=_FP_V1,
        device_fingerprint_v2=v2,
        revoked_at=None,
    )
    return sk, device


def _signed_at_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def test_verifier_accepts_v1_only_when_v1_not_deprecated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sk, device = _fresh_device(v2=None)
    app = _make_app(device, v1_deprecated=False, monkeypatch=monkeypatch)
    body = b'{"ok":true}'
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=None,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-1",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 200


def test_verifier_rejects_v1_only_when_tenant_v1_deprecated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sk, device = _fresh_device(v2=None)
    app = _make_app(device, v1_deprecated=True, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=None,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-2",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "v1 fingerprint deprecated for tenant"


def test_verifier_accepts_matching_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, device = _fresh_device(v2=_FP_V2)
    app = _make_app(device, v1_deprecated=True, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-3",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 200


def test_verifier_rejects_mismatched_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, device = _fresh_device(v2=_FP_V2)
    app = _make_app(device, v1_deprecated=False, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2_OTHER,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-4",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "fingerprint_v2 mismatch"


def test_verifier_400s_on_malformed_v2_header(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, device = _fresh_device(v2=_FP_V2)
    app = _make_app(device, v1_deprecated=False, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2="sha256v2:not-hex-data",
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-5",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 400


def test_verifier_accepts_v2_header_when_stored_v2_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored device predates v2. Client already sending v2. Accept during overlap."""
    sk, device = _fresh_device(v2=None)
    app = _make_app(device, v1_deprecated=False, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-6",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 200


def test_verifier_rejects_v1_mismatch_before_v2_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v1 mismatch is 401 even when v2 matches — defence in depth."""
    sk, device = _fresh_device(v2=_FP_V2)
    app = _make_app(device, v1_deprecated=False, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1="sha256:" + "0" * 64,  # doesn't match stored
        v2=_FP_V2,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-7",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "fingerprint mismatch"


def test_verifier_rejects_signed_at_in_future(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, device = _fresh_device()
    app = _make_app(device, monkeypatch=monkeypatch)
    body = b"{}"
    future = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=future,
        idempotency_key="idem-8",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401


def test_verifier_rejects_stale_signed_at(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, device = _fresh_device()
    app = _make_app(device, monkeypatch=monkeypatch)
    body = b"{}"
    # SIGNATURE_FRESHNESS_MINUTES = 30; pick a window comfortably outside it.
    stale = (datetime.now(UTC) - timedelta(minutes=45)).isoformat().replace("+00:00", "Z")
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=stale,
        idempotency_key="idem-stale",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "signed_at too old"


def test_verifier_rejects_unknown_device(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, _ = _fresh_device()
    app = _make_app(None, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-9",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401


def test_verifier_rejects_revoked_device(monkeypatch: pytest.MonkeyPatch) -> None:
    sk, device = _fresh_device()
    revoked = TerminalDevice(
        id=device.id,
        tenant_id=device.tenant_id,
        terminal_id=device.terminal_id,
        public_key=device.public_key,
        device_fingerprint=device.device_fingerprint,
        device_fingerprint_v2=device.device_fingerprint_v2,
        revoked_at=datetime.now(UTC),
    )
    app = _make_app(revoked, monkeypatch=monkeypatch)
    body = b"{}"
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=5,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-10",
    )
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401


def test_verifier_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signature over the wrong canonical — terminal-id mismatch."""
    sk, device = _fresh_device()
    app = _make_app(device, monkeypatch=monkeypatch)
    body = b"{}"
    # Sign with terminal_id=999 but send terminal_id=5
    headers = _build_signed_headers(
        sk=sk,
        terminal_id=999,
        v1=_FP_V1,
        v2=_FP_V2,
        body=body,
        signed_at=_signed_at_now(),
        idempotency_key="idem-11",
    )
    headers["X-Terminal-Id"] = "5"
    r = TestClient(app).post("/verify", content=body, headers=headers)
    assert r.status_code == 401
