"""Server-side verification + ledger for one-time override tokens.

Privileged POS actions (void, no-sale drawer, price override, reconciliation
retry) require an ``X-Override-Token`` header carrying a device-signed
``OverrideTokenEnvelope``. The verifier:

1. Verifies the Ed25519 device signature on the claim.
2. Confirms the claim's ``code_id`` was registered in the grant (via
   ``pos.grants_issued``).
3. Atomically inserts into ``pos.override_consumptions`` — a PK conflict
   on ``(grant_id, code_id)`` returns 409 ``override_already_consumed``
   and prevents the business write from executing.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §8.8.6.
"""

from __future__ import annotations

import json
from base64 import urlsafe_b64decode
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datapulse.pos.devices import DeviceProof, device_token_verifier, verify_signature
from datapulse.pos.models import OverrideTokenEnvelope


def _pad_b64url(s: str) -> bytes:
    return urlsafe_b64decode(s + "=" * (-len(s) % 4))


def override_token_verifier(expected_action: str):
    """Return a FastAPI dependency that verifies + consumes an override token.

    Usage::

        @router.post("/.../void",
                     dependencies=[Depends(override_token_verifier("void"))])
    """
    from datapulse.core.auth import get_tenant_session

    async def _dep(
        request: Request,
        proof: DeviceProof = Depends(device_token_verifier),  # noqa: B008
        x_override_token: str = Header(..., alias="X-Override-Token"),  # noqa: B008
        session: Session = Depends(get_tenant_session),  # noqa: B008
    ) -> OverrideTokenEnvelope:
        try:
            env_dict = json.loads(_pad_b64url(x_override_token).decode())
            env = OverrideTokenEnvelope.model_validate(env_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail="invalid X-Override-Token") from e

        claim = env.claim

        if claim.action != expected_action:
            raise HTTPException(status_code=403, detail="override action mismatch")
        if claim.terminal_id != proof.terminal_id:
            raise HTTPException(status_code=401, detail="override terminal mismatch")

        msg = claim.model_dump_json().encode()
        sig = _pad_b64url(env.signature)
        if not verify_signature(proof.device.public_key, msg, sig):
            raise HTTPException(status_code=401, detail="override signature invalid")

        row = (
            session.execute(
                text(
                    """SELECT code_ids, offline_expires_at
                     FROM pos.grants_issued WHERE grant_id = :g"""
                ),
                {"g": claim.grant_id},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(status_code=401, detail="invalid grant_id")
        if claim.code_id not in row["code_ids"]:
            raise HTTPException(status_code=401, detail="invalid code_id")
        if row["offline_expires_at"] < datetime.now(UTC):
            raise HTTPException(status_code=401, detail="grant expired")

        try:
            session.execute(
                text(
                    """
                    INSERT INTO pos.override_consumptions
                        (grant_id, code_id, tenant_id, terminal_id, shift_id,
                         action, action_subject_id, consumed_at, request_idempotency_key)
                    VALUES (:g, :c, :tid, :term, :shift, :act, :sub, :cons, :idem)
                    """
                ),
                {
                    "g": claim.grant_id,
                    "c": claim.code_id,
                    "tid": claim.tenant_id,
                    "term": claim.terminal_id,
                    "shift": claim.shift_id,
                    "act": claim.action,
                    "sub": claim.action_subject_id,
                    "cons": claim.consumed_at,
                    "idem": proof.idempotency_key,
                },
            )
        except IntegrityError as e:
            session.rollback()
            raise HTTPException(status_code=409, detail="override_already_consumed") from e

        return env

    return _dep
