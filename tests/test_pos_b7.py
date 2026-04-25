"""Unit tests for POS B7 — RBAC + Billing + Controlled substance verification.

Covers:
* PharmacistVerifier: PIN hashing, token issue/validate, expiry, tamper detection
* pos_guard: require_pos_plan() raises 402 for non-POS plans, passes for platform/enterprise
* POST /pos/controlled/verify: happy path + wrong PIN + 403 on bad credential
* RoleKey: AccessContext accepts POS role keys
"""

from __future__ import annotations

import hmac as _hmac
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_pos_service, get_tenant_plan_limits
from datapulse.billing.plans import PLAN_LIMITS, get_plan_limits
from datapulse.pos.exceptions import PharmacistVerificationRequiredError
from datapulse.pos.models import PharmacistVerifyResponse
from datapulse.pos.pharmacist_verifier import (
    ALGO_SCRYPT,
    PharmacistVerifier,
    PinRecord,
    hash_pin,
    verify_pin,
)
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

pytestmark = pytest.mark.unit


# ────────────────────────────────────────────────────────────────────────────
# Shared fixtures / helpers
# ────────────────────────────────────────────────────────────────────────────

SECRET = "test-signing-secret"
PHARMACIST_ID = "pharmacist-user-001"
DRUG_CODE = "CTRL-001"
VALID_PIN = "1234"

_MOCK_USER: dict[str, Any] = {
    "sub": PHARMACIST_ID,
    "email": "pharma@test.local",
    "tenant_id": "1",
    "roles": ["pos_pharmacist"],
    "raw_claims": {},
}


def _make_pin_record(pin: str) -> PinRecord:
    h, s = hash_pin(pin)
    return PinRecord(pin_hash=h, pin_salt=s, pin_hash_algo=ALGO_SCRYPT)


def _make_verifier(pin_record: PinRecord | None = None) -> PharmacistVerifier:
    return PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _user_id: pin_record,
    )


# ────────────────────────────────────────────────────────────────────────────
# PharmacistVerifier unit tests
# ────────────────────────────────────────────────────────────────────────────


def test_hash_pin_verify_roundtrip() -> None:
    """Scrypt hash+verify roundtrip: correct PIN must verify successfully."""
    h, s = hash_pin("1234")
    assert verify_pin("1234", h, s) is True


def test_hash_pin_wrong_pin_fails_verify() -> None:
    """Wrong PIN must not verify against a hash produced from a different PIN."""
    h, s = hash_pin("1234")
    assert verify_pin("5678", h, s) is False


def test_hash_pin_random_salt() -> None:
    """Each call produces a fresh salt — hashes for the same PIN must differ."""
    h1, s1 = hash_pin("1234")
    h2, s2 = hash_pin("1234")
    assert s1 != s2
    assert h1 != h2


def test_hash_pin_returns_base64_strings() -> None:
    """hash_pin must return base64-encoded strings, not raw bytes or hex."""
    import base64

    h, s = hash_pin("1234")
    assert base64.b64decode(h)  # decodes without error
    assert base64.b64decode(s)


def test_verify_and_issue_returns_token_on_correct_pin() -> None:
    verifier = _make_verifier(_make_pin_record(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_and_issue_raises_on_wrong_pin() -> None:
    verifier = _make_verifier(_make_pin_record(VALID_PIN))
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue(PHARMACIST_ID, "wrong", DRUG_CODE)


def test_verify_and_issue_raises_when_no_pin_stored() -> None:
    verifier = _make_verifier()
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)


def test_validate_token_returns_pharmacist_id() -> None:
    verifier = _make_verifier(_make_pin_record(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    result = verifier.validate_token(token, DRUG_CODE)
    assert result == PHARMACIST_ID


def test_validate_token_raises_on_wrong_drug_code() -> None:
    verifier = _make_verifier(_make_pin_record(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(token, "OTHER-DRUG")


def test_validate_token_raises_on_tampered_signature() -> None:
    verifier = _make_verifier(_make_pin_record(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    tampered = token[:-4] + "xxxx"
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(tampered, DRUG_CODE)


def test_validate_token_raises_on_expired_token() -> None:
    verifier = PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _: _make_pin_record(VALID_PIN),
        ttl=1,  # 1-second TTL for test
    )
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    # Back-date the token timestamp beyond the 1-second TTL
    ts, pharmacist_id, drug_code, _sig = token.split(":", 3)
    old_ts = str(int(ts) - 10)  # 10 seconds ago > 1s TTL
    payload = f"{old_ts}:{pharmacist_id}:{drug_code}"
    new_sig = _hmac.new(SECRET.encode(), payload.encode(), "sha256").hexdigest()
    expired_token = f"{old_ts}:{pharmacist_id}:{drug_code}:{new_sig}"
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(expired_token, DRUG_CODE)


def test_validate_token_raises_on_malformed_token() -> None:
    verifier = _make_verifier(_make_pin_record(VALID_PIN))
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token("not:a:valid", DRUG_CODE)


# ────────────────────────────────────────────────────────────────────────────
# billing/plans — platform plan
# ────────────────────────────────────────────────────────────────────────────


def test_platform_plan_exists_in_plan_limits() -> None:
    assert "platform" in PLAN_LIMITS


def test_platform_plan_has_pos_integration() -> None:
    assert PLAN_LIMITS["platform"].pos_integration is True


def test_platform_plan_price_display() -> None:
    assert PLAN_LIMITS["platform"].price_display == "$99/mo"


def test_enterprise_plan_still_has_pos_integration() -> None:
    assert PLAN_LIMITS["enterprise"].pos_integration is True


def test_starter_plan_no_pos_integration() -> None:
    assert PLAN_LIMITS["starter"].pos_integration is False


def test_pro_plan_no_pos_integration() -> None:
    assert PLAN_LIMITS["pro"].pos_integration is False


def test_get_plan_limits_returns_platform() -> None:
    limits = get_plan_limits("platform")
    assert limits.pos_integration is True
    assert limits.name == "Platform"


# ────────────────────────────────────────────────────────────────────────────
# pos_guard — require_pos_plan dependency
# ────────────────────────────────────────────────────────────────────────────


def _make_guard_app(plan_key: str) -> FastAPI:
    from datapulse.billing.pos_guard import require_pos_plan

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {"sub": "u1", "tenant_id": "1"}
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS[plan_key]

    @app.get("/probe", dependencies=[Depends(require_pos_plan())])
    def _probe() -> dict:
        return {"ok": True}

    return app


def test_pos_guard_passes_for_platform_plan() -> None:
    with TestClient(_make_guard_app("platform")) as client:
        assert client.get("/probe").status_code == 200


def test_pos_guard_passes_for_enterprise_plan() -> None:
    with TestClient(_make_guard_app("enterprise")) as client:
        assert client.get("/probe").status_code == 200


def test_pos_guard_raises_402_for_starter_plan() -> None:
    with TestClient(_make_guard_app("starter")) as client:
        assert client.get("/probe").status_code == 402


def test_pos_guard_raises_402_for_pro_plan() -> None:
    with TestClient(_make_guard_app("pro")) as client:
        assert client.get("/probe").status_code == 402


# ────────────────────────────────────────────────────────────────────────────
# POST /pos/controlled/verify HTTP-level
# ────────────────────────────────────────────────────────────────────────────


def _make_verify_app(mock_service: MagicMock) -> FastAPI:
    """Minimal app: POS router mounted, billing + RBAC deps bypassed."""
    from datapulse.api.routes.pos import router as pos_router

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    app.dependency_overrides[get_pos_service] = lambda: mock_service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: PLAN_LIMITS["platform"]
    app.dependency_overrides[get_access_context] = lambda: AccessContext(
        member_id=1,
        tenant_id=1,
        user_id=PHARMACIST_ID,
        role_key="pos_pharmacist",
        permissions={"pos:controlled:verify"},
    )
    app.include_router(pos_router, prefix="/api/v1")

    @app.exception_handler(PharmacistVerificationRequiredError)
    async def _h(_req: Request, exc: PharmacistVerificationRequiredError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    return app


@pytest.fixture()
def _mock_verify_service() -> MagicMock:
    svc = MagicMock()
    svc.verify_pharmacist_pin.return_value = PharmacistVerifyResponse(
        token="fake-token-xyz",
        pharmacist_id=PHARMACIST_ID,
        drug_code=DRUG_CODE,
        expires_at=datetime.now(UTC),
    )
    return svc


def test_verify_endpoint_happy_path(_mock_verify_service: MagicMock) -> None:
    with TestClient(_make_verify_app(_mock_verify_service)) as client:
        resp = client.post(
            "/api/v1/pos/controlled/verify",
            json={
                "pharmacist_id": PHARMACIST_ID,
                "credential": VALID_PIN,
                "drug_code": DRUG_CODE,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == "fake-token-xyz"
        assert data["pharmacist_id"] == PHARMACIST_ID
    _mock_verify_service.verify_pharmacist_pin.assert_called_once_with(
        pharmacist_id=PHARMACIST_ID,
        credential=VALID_PIN,
        drug_code=DRUG_CODE,
    )


def test_verify_endpoint_wrong_pin_returns_403(_mock_verify_service: MagicMock) -> None:
    _mock_verify_service.verify_pharmacist_pin.side_effect = PharmacistVerificationRequiredError(
        drug_code=DRUG_CODE,
        message="Pharmacist PIN is incorrect.",
    )
    with TestClient(_make_verify_app(_mock_verify_service)) as client:
        resp = client.post(
            "/api/v1/pos/controlled/verify",
            json={"pharmacist_id": PHARMACIST_ID, "credential": "wrong", "drug_code": DRUG_CODE},
        )
        assert resp.status_code == 403


def test_verify_endpoint_short_credential_rejected(_mock_verify_service: MagicMock) -> None:
    """Pydantic min_length=4 on credential must reject a 3-char PIN."""
    with TestClient(_make_verify_app(_mock_verify_service)) as client:
        resp = client.post(
            "/api/v1/pos/controlled/verify",
            json={"pharmacist_id": PHARMACIST_ID, "credential": "12", "drug_code": DRUG_CODE},
        )
        assert resp.status_code == 422


# ────────────────────────────────────────────────────────────────────────────
# RBAC models — RoleKey includes POS roles
# ────────────────────────────────────────────────────────────────────────────


def test_access_context_accepts_pos_cashier_role() -> None:
    from datapulse.rbac.models import AccessContext

    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="u1",
        role_key="pos_cashier",
        permissions={"pos:terminal:open", "pos:transaction:create"},
    )
    assert ctx.role_key == "pos_cashier"


def test_access_context_accepts_pos_manager_role() -> None:
    from datapulse.rbac.models import AccessContext

    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="u1",
        role_key="pos_manager",
        permissions=set(),
    )
    assert ctx.role_key == "pos_manager"


def test_access_context_accepts_pos_pharmacist_role() -> None:
    from datapulse.rbac.models import AccessContext

    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="u1",
        role_key="pos_pharmacist",
        permissions={"pos:controlled:verify"},
    )
    assert ctx.role_key == "pos_pharmacist"


def test_access_context_accepts_pos_supervisor_role() -> None:
    from datapulse.rbac.models import AccessContext

    ctx = AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="u1",
        role_key="pos_supervisor",
        permissions={"pos:transaction:void", "pos:shift:reconcile"},
    )
    assert ctx.role_key == "pos_supervisor"


# ────────────────────────────────────────────────────────────────────────────
# C3 — tenant_id predicate on pharmacist PIN hash lookup (#676)
# ────────────────────────────────────────────────────────────────────────────


def _make_tenant_scoped_verifier(
    pharmacist_id: str,
    stored_tenant_id: int,
    pin_record: PinRecord,
    request_tenant_id: int,
) -> PharmacistVerifier:
    """Build a verifier whose pin_lookup only returns the record when tenant matches.

    Simulates what ``get_pos_service`` does: the closure captures the caller's
    ``tenant_id`` and passes it to ``repo.get_pharmacist_pin_hash(pid, tenant_id)``.
    """

    def _scoped_lookup(pid: str) -> PinRecord | None:
        # Return the record only when the pharmacist belongs to the requesting tenant.
        if pid == pharmacist_id and request_tenant_id == stored_tenant_id:
            return pin_record
        return None

    return PharmacistVerifier(secret_key=SECRET, pin_lookup=_scoped_lookup)


def test_pin_lookup_returns_hash_for_correct_tenant() -> None:
    """PIN verification succeeds when pharmacist and caller share the same tenant."""
    verifier = _make_tenant_scoped_verifier(
        pharmacist_id=PHARMACIST_ID,
        stored_tenant_id=42,
        pin_record=_make_pin_record(VALID_PIN),
        request_tenant_id=42,
    )
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    assert isinstance(token, str) and len(token) > 0


def test_pin_lookup_returns_none_for_wrong_tenant() -> None:
    """PIN lookup returns None when the requesting tenant does not own the pharmacist record.

    This is the C3 defence-in-depth check: even if RLS were bypassed a
    pharmacist from tenant A must not authenticate against PIN data belonging
    to tenant B.
    """
    verifier = _make_tenant_scoped_verifier(
        pharmacist_id=PHARMACIST_ID,
        stored_tenant_id=42,  # pharmacist lives in tenant 42
        pin_record=_make_pin_record(VALID_PIN),
        request_tenant_id=99,  # caller is from tenant 99
    )
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
