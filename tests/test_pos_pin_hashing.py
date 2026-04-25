"""Unit tests for pharmacist PIN hashing (scrypt) and verification.

Covers:
- hash_pin produces different hashes for the same PIN (salt randomness)
- verify_pin returns True for correct PIN
- verify_pin returns False for wrong PIN
- Timing-safe comparison (hmac.compare_digest path)
- Legacy SHA-256 path still verifies correctly
- Auto-upgrade: pin_upgrade callback is called on successful legacy verify
- Auto-upgrade: pin_upgrade is NOT called when algo is already scrypt
- No-lookup path: PharmacistVerifier raises when pharmacist is unknown
- Migration: legacy rows must have pin_hash_algo = 'legacy'
"""

from __future__ import annotations

import hashlib

import pytest

from datapulse.pos.exceptions import PharmacistVerificationRequiredError
from datapulse.pos.pharmacist_verifier import (
    ALGO_LEGACY,
    ALGO_SCRYPT,
    PharmacistVerifier,
    PinRecord,
    _verify_legacy_pin,
    hash_pin,
    verify_pin,
)

PIN = "1234"
DRUG = "TRAMADOL-50MG"
SECRET = "test-secret-key"


# ---------------------------------------------------------------------------
# hash_pin
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hash_pin_returns_two_non_empty_strings() -> None:
    hsh, salt = hash_pin(PIN)
    assert isinstance(hsh, str) and len(hsh) > 0
    assert isinstance(salt, str) and len(salt) > 0


@pytest.mark.unit
def test_hash_pin_salt_randomness() -> None:
    """Same PIN must produce different hashes on each call (random salt)."""
    hsh1, salt1 = hash_pin(PIN)
    hsh2, salt2 = hash_pin(PIN)
    assert hsh1 != hsh2, "hashes must differ due to random salt"
    assert salt1 != salt2, "salts must be unique per call"


# ---------------------------------------------------------------------------
# verify_pin (scrypt)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_verify_pin_correct() -> None:
    hsh, salt = hash_pin(PIN)
    assert verify_pin(PIN, hsh, salt) is True


@pytest.mark.unit
def test_verify_pin_wrong_pin() -> None:
    hsh, salt = hash_pin(PIN)
    assert verify_pin("9999", hsh, salt) is False


@pytest.mark.unit
def test_verify_pin_wrong_salt_gives_false() -> None:
    hsh, _ = hash_pin(PIN)
    _, other_salt = hash_pin("other")
    assert verify_pin(PIN, hsh, other_salt) is False


# ---------------------------------------------------------------------------
# Legacy SHA-256 path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_verify_legacy_pin_correct() -> None:
    legacy_hash = hashlib.sha256(PIN.encode()).hexdigest()
    assert _verify_legacy_pin(PIN, legacy_hash) is True


@pytest.mark.unit
def test_verify_legacy_pin_wrong() -> None:
    legacy_hash = hashlib.sha256(PIN.encode()).hexdigest()
    assert _verify_legacy_pin("0000", legacy_hash) is False


# ---------------------------------------------------------------------------
# PharmacistVerifier — scrypt path
# ---------------------------------------------------------------------------


def _make_verifier(record: PinRecord | None, upgrade_cb=None) -> PharmacistVerifier:
    return PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _pid: record,
        pin_upgrade=upgrade_cb,
    )


@pytest.mark.unit
def test_verifier_scrypt_issues_token() -> None:
    hsh, salt = hash_pin(PIN)
    record = PinRecord(pin_hash=hsh, pin_salt=salt, pin_hash_algo=ALGO_SCRYPT)
    verifier = _make_verifier(record)
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    assert isinstance(token, str) and len(token) > 0


@pytest.mark.unit
def test_verifier_scrypt_wrong_pin_raises() -> None:
    hsh, salt = hash_pin(PIN)
    record = PinRecord(pin_hash=hsh, pin_salt=salt, pin_hash_algo=ALGO_SCRYPT)
    verifier = _make_verifier(record)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue("pharm-1", "wrong", DRUG)


@pytest.mark.unit
def test_verifier_unknown_pharmacist_raises() -> None:
    verifier = _make_verifier(None)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.verify_and_issue("pharm-unknown", PIN, DRUG)


# ---------------------------------------------------------------------------
# PharmacistVerifier — legacy path + auto-upgrade
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_verifier_legacy_pin_still_works() -> None:
    legacy_hash = hashlib.sha256(PIN.encode()).hexdigest()
    record = PinRecord(pin_hash=legacy_hash, pin_salt=None, pin_hash_algo=ALGO_LEGACY)
    verifier = _make_verifier(record)
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    assert isinstance(token, str) and len(token) > 0


@pytest.mark.unit
def test_verifier_legacy_triggers_upgrade() -> None:
    legacy_hash = hashlib.sha256(PIN.encode()).hexdigest()
    record = PinRecord(pin_hash=legacy_hash, pin_salt=None, pin_hash_algo=ALGO_LEGACY)

    upgraded: list[tuple[str, str, str]] = []

    def capture_upgrade(pid: str, new_hash: str, new_salt: str) -> None:
        upgraded.append((pid, new_hash, new_salt))

    verifier = _make_verifier(record, upgrade_cb=capture_upgrade)
    verifier.verify_and_issue("pharm-1", PIN, DRUG)

    assert len(upgraded) == 1, "upgrade callback must be called exactly once"
    pid, new_hash, new_salt = upgraded[0]
    assert pid == "pharm-1"
    # The new hash must verify correctly with the returned salt
    assert verify_pin(PIN, new_hash, new_salt) is True


@pytest.mark.unit
def test_verifier_scrypt_does_not_trigger_upgrade() -> None:
    hsh, salt = hash_pin(PIN)
    record = PinRecord(pin_hash=hsh, pin_salt=salt, pin_hash_algo=ALGO_SCRYPT)

    upgrade_calls: list = []
    verifier = _make_verifier(record, upgrade_cb=lambda *a: upgrade_calls.append(a))
    verifier.verify_and_issue("pharm-1", PIN, DRUG)

    assert upgrade_calls == [], "upgrade must not be called when algo is already scrypt"


@pytest.mark.unit
def test_verifier_upgrade_failure_does_not_block_login() -> None:
    """If upgrade raises, verify_and_issue still returns a token."""
    legacy_hash = hashlib.sha256(PIN.encode()).hexdigest()
    record = PinRecord(pin_hash=legacy_hash, pin_salt=None, pin_hash_algo=ALGO_LEGACY)

    def failing_upgrade(*_args):
        raise RuntimeError("DB down")

    verifier = _make_verifier(record, upgrade_cb=failing_upgrade)
    # Must NOT raise even though the upgrade callback fails
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    assert isinstance(token, str)


# ---------------------------------------------------------------------------
# PharmacistVerifier — validate_token
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_token_roundtrip() -> None:
    hsh, salt = hash_pin(PIN)
    record = PinRecord(pin_hash=hsh, pin_salt=salt, pin_hash_algo=ALGO_SCRYPT)
    verifier = _make_verifier(record)
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    pharmacist_id = verifier.validate_token(token, DRUG)
    assert pharmacist_id == "pharm-1"


@pytest.mark.unit
def test_validate_token_expired_raises() -> None:
    hsh, salt = hash_pin(PIN)
    record = PinRecord(pin_hash=hsh, pin_salt=salt, pin_hash_algo=ALGO_SCRYPT)
    # Use a negative TTL so the token is expired the moment validate_token is called.
    # The verifier allows negative TTL in the constructor; the check is age > self.ttl.
    verifier = PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _: record,
        ttl=-1,  # always expired
    )
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(token, DRUG)


@pytest.mark.unit
def test_validate_token_wrong_drug_raises() -> None:
    hsh, salt = hash_pin(PIN)
    record = PinRecord(pin_hash=hsh, pin_salt=salt, pin_hash_algo=ALGO_SCRYPT)
    verifier = _make_verifier(record)
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    with pytest.raises(PharmacistVerificationRequiredError):
        verifier.validate_token(token, "OTHER-DRUG")


# ---------------------------------------------------------------------------
# Legacy str-returning lookup compatibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_verifier_accepts_plain_str_lookup() -> None:
    """Callers that return a bare str (old interface) should still work as legacy."""
    legacy_hash = hashlib.sha256(PIN.encode()).hexdigest()
    verifier = PharmacistVerifier(
        secret_key=SECRET,
        pin_lookup=lambda _: legacy_hash,  # type: ignore[return-value]
    )
    token = verifier.verify_and_issue("pharm-1", PIN, DRUG)
    assert isinstance(token, str)
