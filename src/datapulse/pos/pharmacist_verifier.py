"""Pharmacist PIN verification for controlled-substance dispensing.

Design
------
* The pharmacist's PIN is hashed with ``scrypt`` (n=2^14, r=8, p=1) plus a
  32-byte per-user random salt, both stored as base64 TEXT in
  ``tenant_members.pharmacist_pin_hash`` and ``tenant_members.pharmacist_pin_salt``.
  The column ``tenant_members.pharmacist_pin_hash_algo`` distinguishes scrypt hashes
  from legacy SHA-256 rows (value ``'legacy'``).
* Legacy rows (SHA-256, no salt) are auto-upgraded to scrypt on the first
  successful login, so the transition is zero-downtime.
* Verification issues a short-lived HMAC-signed token (5 min TTL).
* The token is opaque to the client: ``{ts}:{pharmacist_id}:{drug_code}:{sig}``.
* Subsequent ``add_item`` calls pass this token as ``pharmacist_id``; the
  service calls ``validate_token`` before accepting the controlled-substance item.
* Uses ``hmac.compare_digest`` throughout for timing-safe comparison.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from datapulse.logging import get_logger
from datapulse.pos.exceptions import PharmacistVerificationRequiredError

log = get_logger(__name__)

# Token is valid for 5 minutes.
TOKEN_TTL_SECONDS: int = 300
_SEP = ":"

# scrypt parameters — OWASP recommended minimum for interactive use
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_SALT_BYTES = 32
_SCRYPT_DK_LEN = 32

ALGO_SCRYPT = "scrypt"
ALGO_LEGACY = "legacy"


# ---------------------------------------------------------------------------
# Data carrier for a single pharmacist's PIN fields
# ---------------------------------------------------------------------------


class PinRecord(NamedTuple):
    """All PIN-related fields fetched from the DB for a single pharmacist."""

    pin_hash: str
    pin_salt: str | None = None
    pin_hash_algo: str = ALGO_LEGACY


# ---------------------------------------------------------------------------
# Helpers — pure functions, no I/O
# ---------------------------------------------------------------------------


def hash_pin(pin: str) -> tuple[str, str]:
    """Hash a PIN with scrypt + a fresh random salt.

    Returns
    -------
    (hash_b64, salt_b64)
        Both are standard base64-encoded strings safe to store as TEXT columns.
    """
    salt = os.urandom(_SCRYPT_SALT_BYTES)
    dk = hashlib.scrypt(
        pin.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DK_LEN,
    )
    return (
        base64.b64encode(dk).decode("ascii"),
        base64.b64encode(salt).decode("ascii"),
    )


def verify_pin(pin: str, stored_hash: str, stored_salt: str) -> bool:
    """Timing-safe verification of a scrypt-hashed PIN.

    Parameters
    ----------
    pin:
        Plaintext PIN provided by the pharmacist.
    stored_hash:
        base64-encoded scrypt digest from the database.
    stored_salt:
        base64-encoded 32-byte salt from the database.
    """
    salt = base64.b64decode(stored_salt)
    dk = hashlib.scrypt(
        pin.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DK_LEN,
    )
    candidate = base64.b64encode(dk).decode("ascii")
    return hmac.compare_digest(stored_hash, candidate)


def _verify_legacy_pin(pin: str, stored_hash: str) -> bool:
    """Timing-safe verification against the old SHA-256 (no salt) hash."""
    candidate = hashlib.sha256(pin.encode("utf-8")).hexdigest()
    return hmac.compare_digest(stored_hash, candidate)


def _sign(secret: str, message: str) -> str:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), "sha256").hexdigest()


def _make_token(secret: str, pharmacist_id: str, drug_code: str, ts: int) -> str:
    """Build a signed token: ``{ts}:{pharmacist_id}:{drug_code}:{sig}``."""
    payload = f"{ts}{_SEP}{pharmacist_id}{_SEP}{drug_code}"
    sig = _sign(secret, payload)
    return f"{payload}{_SEP}{sig}"


def _parse_token(token: str) -> tuple[int, str, str, str] | None:
    """Parse token into (ts, pharmacist_id, drug_code, sig).  Returns None on bad format."""
    parts = token.split(_SEP, 3)
    if len(parts) != 4:
        return None
    ts_str, pharmacist_id, drug_code, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return None
    return ts, pharmacist_id, drug_code, sig


# ---------------------------------------------------------------------------
# Verifier — holds the signing secret, wires to DB via lookup callables
# ---------------------------------------------------------------------------


@dataclass
class PharmacistVerifier:
    """Stateless verifier for pharmacist PIN challenges.

    Parameters
    ----------
    secret_key:
        Application secret used to sign/verify tokens.  Must be set in
        ``Settings.secret_key`` (not empty in production).
    pin_lookup:
        Callable ``(pharmacist_id: str) -> PinRecord | str | None`` that returns
        a :class:`PinRecord` (or the legacy ``str`` hash) for a given user ID,
        or ``None`` if the user is not a pharmacist.  Legacy callers that return
        a bare ``str`` are treated as ALGO_LEGACY rows automatically.
        Injected at construction time so this module stays free of SQLAlchemy imports.
    pin_upgrade:
        Optional callable ``(pharmacist_id: str, new_hash: str, new_salt: str) -> None``
        invoked after a successful legacy-PIN verification to auto-upgrade the
        stored hash to scrypt.  If ``None``, auto-upgrade is skipped (no-op).
    ttl:
        Token TTL in seconds (default: ``TOKEN_TTL_SECONDS`` = 300).
    """

    secret_key: str
    pin_lookup: Callable[[str], PinRecord | str | None]
    pin_upgrade: Callable[[str, str, str], None] | None = None
    ttl: int = TOKEN_TTL_SECONDS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify_and_issue(self, pharmacist_id: str, credential: str, drug_code: str) -> str:
        """Validate PIN and return a signed token.

        Raises
        ------
        PharmacistVerificationRequiredError
            When the credential is wrong or the user has no PIN hash stored.
        """
        raw = self.pin_lookup(pharmacist_id)
        if raw is None:
            log.warning("pos.pharmacist.no_pin_hash", pharmacist_id=pharmacist_id)
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message=(
                    f"Pharmacist {pharmacist_id!r} is not registered"
                    " for controlled-substance dispensing."
                ),
            )

        # Support both legacy str-returning lookups and new PinRecord lookups.
        record: PinRecord = raw if isinstance(raw, PinRecord) else PinRecord(pin_hash=raw)

        if record.pin_hash_algo == ALGO_SCRYPT:
            if record.pin_salt is None:
                log.error(
                    "pos.pharmacist.scrypt_no_salt",
                    pharmacist_id=pharmacist_id,
                )
                raise PharmacistVerificationRequiredError(
                    drug_code=drug_code,
                    message="Pharmacist PIN storage is corrupt (scrypt hash missing salt).",
                )
            ok = verify_pin(credential, record.pin_hash, record.pin_salt)
        else:
            # Legacy SHA-256 path
            ok = _verify_legacy_pin(credential, record.pin_hash)

        if not ok:
            log.warning("pos.pharmacist.wrong_pin", pharmacist_id=pharmacist_id)
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Pharmacist PIN is incorrect.",
            )

        # Auto-upgrade legacy hash to scrypt on successful verification (best-effort)
        if record.pin_hash_algo == ALGO_LEGACY and self.pin_upgrade is not None:
            try:
                new_hash, new_salt = hash_pin(credential)
                self.pin_upgrade(pharmacist_id, new_hash, new_salt)
                log.info(
                    "pos.pharmacist.pin_upgraded_to_scrypt",
                    pharmacist_id=pharmacist_id,
                )
            except Exception:  # noqa: BLE001
                # Upgrade is best-effort — never block a successful verify
                log.warning(
                    "pos.pharmacist.pin_upgrade_failed",
                    pharmacist_id=pharmacist_id,
                )

        ts = int(time.time())
        token = _make_token(self.secret_key, pharmacist_id, drug_code, ts)
        log.info("pos.pharmacist.verified", pharmacist_id=pharmacist_id, drug_code=drug_code)
        return token

    def validate_token(self, token: str, drug_code: str) -> str:
        """Validate a previously issued token.

        Returns the ``pharmacist_id`` embedded in the token.

        Raises
        ------
        PharmacistVerificationRequiredError
            When the token is malformed, expired, tampered with, or issued
            for a different ``drug_code``.
        """
        parsed = _parse_token(token)
        if parsed is None:
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Invalid pharmacist verification token format.",
            )

        ts, pharmacist_id, token_drug_code, sig = parsed

        # 1. Replay-window check
        age = int(time.time()) - ts
        if age < 0 or age > self.ttl:
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message=f"Pharmacist verification token has expired (age={age}s).",
            )

        # 2. Drug-code binding
        if not hmac.compare_digest(token_drug_code, drug_code):
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Pharmacist token was issued for a different drug code.",
            )

        # 3. Signature check (timing-safe)
        payload = f"{ts}{_SEP}{pharmacist_id}{_SEP}{token_drug_code}"
        expected_sig = _sign(self.secret_key, payload)
        if not hmac.compare_digest(sig, expected_sig):
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Pharmacist verification token signature is invalid.",
            )

        return pharmacist_id
