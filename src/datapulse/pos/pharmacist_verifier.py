"""Pharmacist PIN verification for controlled-substance dispensing.

Design
------
* The pharmacist's PIN is stored as a SHA-256 hex digest in
  ``tenant_members.pharmacist_pin_hash`` (added by migration 076).
* Verification issues a short-lived HMAC-signed token (5 min TTL).
* The token is opaque to the client: ``{ts}:{pharmacist_id}:{drug_code}:{sig}``.
* Subsequent ``add_item`` calls pass this token as ``pharmacist_id``; the
  service calls ``validate_token`` before accepting the controlled-substance item.
* Uses ``hmac.compare_digest`` throughout for timing-safe comparison.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass

from datapulse.logging import get_logger
from datapulse.pos.exceptions import PharmacistVerificationRequiredError

log = get_logger(__name__)

# Token is valid for 5 minutes.
TOKEN_TTL_SECONDS: int = 300
_SEP = ":"


# ---------------------------------------------------------------------------
# Helpers — pure functions, no I/O
# ---------------------------------------------------------------------------


def hash_pin(pin: str) -> str:
    """Return the SHA-256 hex digest of a PIN string."""
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


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
# Verifier — holds the signing secret, wires to DB via a lookup callable
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
        Callable ``(pharmacist_id: str) -> str | None`` that returns the
        stored ``pharmacist_pin_hash`` for a given user ID, or ``None``
        if the user is not a pharmacist.  Injected at construction time
        so this module stays free of SQLAlchemy imports.
    ttl:
        Token TTL in seconds (default: ``TOKEN_TTL_SECONDS`` = 300).
    """

    secret_key: str
    pin_lookup: Callable[[str], str | None]
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
        stored_hash = self.pin_lookup(pharmacist_id)
        if stored_hash is None:
            log.warning("pos.pharmacist.no_pin_hash", pharmacist_id=pharmacist_id)
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message=(
                    f"Pharmacist {pharmacist_id!r} is not registered"
                    " for controlled-substance dispensing."
                ),
            )

        provided_hash = hash_pin(credential)
        if not hmac.compare_digest(stored_hash, provided_hash):
            log.warning("pos.pharmacist.wrong_pin", pharmacist_id=pharmacist_id)
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Pharmacist PIN is incorrect.",
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
