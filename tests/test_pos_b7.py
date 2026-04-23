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
from datapulse.pos.pharmacist_verifier import PharmacistVerifier, hash_pin
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


def _make_verifier(pin_hash: str | None = None) -> PharmacistVerifier:
    return PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _user_id: pin_hash,
    )


# ────────────────────────────────────────────────────────────────────────────
# PharmacistVerifier unit tests
# ────────────────────────────────────────────────────────────────────────────


def test_hash_pin_is_deterministic() -> None:
    assert hash_pin("1234") == hash_pin("1234")


def test_hash_pin_differs_for_different_pins() -> None:
    assert hash_pin("1234") != hash_pin("5678")


def test_hash_pin_is_peppered_not_plain_sha256() -> None:
    """Regression guard: a PIN hash must never equal plain SHA-256 of the PIN.

    Unsalted SHA-256 of a 4–6 digit PIN is rainbow-tableable in milliseconds,
    so this test ensures the peppered-HMAC upgrade sticks.
    """
    import hashlib

    plain = hashlib.sha256(b"1234").hexdigest()
    assert hash_pin("1234") != plain


def test_get_pepper_raises_when_secret_empty_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty secret_key in non-dev environments must NOT silently fall back
    to the public dev pepper — that would leave PIN hashes with the rainbow-
    table resistance of plain SHA-256.
    """
    from datapulse.core.config import get_settings
    from datapulse.pos.pharmacist_verifier import _get_pepper

    settings = get_settings()
    monkeypatch.setattr(settings, "pipeline_webhook_secret", "")
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "sentry_environment", "production")

    with pytest.raises(RuntimeError, match="pipeline_webhook_secret is empty"):
        _get_pepper()


def test_get_pepper_allows_dev_fallback_in_dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dev/test environments may use the fallback pepper so unit tests and
    local boot don't require a real secret_key. Ensures the guard doesn't
    over-reach.
    """
    from datapulse.core.config import get_settings
    from datapulse.pos.pharmacist_verifier import _get_pepper

    settings = get_settings()
    monkeypatch.setattr(settings, "pipeline_webhook_secret", "")
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "sentry_environment", "development")

    pepper = _get_pepper()
    assert isinstance(pepper, bytes)
    assert len(pepper) > 0


def test_verify_and_issue_returns_token_on_correct_pin() -> None:
    verifier = _make_verifier(pin_hash=hash_pin(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_and_issue_raises_on_wrong_pin() -> None:
    verifier = _make_verifier(pin_hash=hash_pin(VALID_PIN))
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue(PHARMACIST_ID, "wrong", DRUG_CODE)


def test_verify_and_issue_raises_when_no_pin_stored() -> None:
    verifier = _make_verifier(pin_hash=None)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)


def test_validate_token_returns_pharmacist_id() -> None:
    verifier = _make_verifier(pin_hash=hash_pin(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    result = verifier.validate_token(token, DRUG_CODE)
    assert result == PHARMACIST_ID


def test_validate_token_raises_on_wrong_drug_code() -> None:
    verifier = _make_verifier(pin_hash=hash_pin(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(token, "OTHER-DRUG")


def test_validate_token_raises_on_tampered_signature() -> None:
    verifier = _make_verifier(pin_hash=hash_pin(VALID_PIN))
    token = verifier.verify_and_issue(PHARMACIST_ID, VALID_PIN, DRUG_CODE)
    tampered = token[:-4] + "xxxx"
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(tampered, DRUG_CODE)


def test_validate_token_raises_on_expired_token() -> None:
    verifier = PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _: hash_pin(VALID_PIN),
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
    verifier = _make_verifier(pin_hash=hash_pin(VALID_PIN))
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
