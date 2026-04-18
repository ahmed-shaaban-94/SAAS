"""POS request idempotency — dedupe retried mutating requests.

Retention (168h) strictly exceeds the provisional queue window (72h), so every
client retry falls inside the server dedupe horizon and double-processing is
impossible even at the edges.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §6.4.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

IDEMPOTENCY_TTL_HOURS: int = 168
PROVISIONAL_TTL_HOURS: int = 72


@dataclass(frozen=True)
class IdempotencyContext:
    """Outcome of check_and_claim for a particular Idempotency-Key."""

    key: str
    request_hash: str
    replay: bool
    cached_status: int | None = None
    cached_body: dict[str, Any] | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def hash_body(body: bytes) -> str:
    """SHA-256 hex digest of the raw request body."""
    return hashlib.sha256(body).hexdigest()


def check_and_claim(
    session: Session,
    key: str,
    tenant_id: int,
    endpoint: str,
    request_hash: str,
) -> IdempotencyContext:
    """Look up ``key`` for ``tenant_id``; if absent, claim a new row.

    Returns ``replay=True`` (with cached response) when a live row with the
    same hash exists. Raises HTTPException(409) on hash mismatch. Treats an
    expired row as absent (deletes + re-claims).
    """
    row = (
        session.execute(
            text(
                """
            SELECT request_hash, response_status, response_body, expires_at
              FROM pos.idempotency_keys
             WHERE key = :key AND tenant_id = :tenant_id
            """
            ),
            {"key": key, "tenant_id": tenant_id},
        )
        .mappings()
        .first()
    )

    if row:
        if row["expires_at"] < _now():
            session.execute(
                text("DELETE FROM pos.idempotency_keys WHERE key = :key AND tenant_id = :tid"),
                {"key": key, "tid": tenant_id},
            )
        else:
            if row["request_hash"] != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key reuse with different request body.",
                )
            return IdempotencyContext(
                key=key,
                request_hash=request_hash,
                replay=True,
                cached_status=row["response_status"],
                cached_body=row["response_body"],
            )

    expires = _now() + timedelta(hours=IDEMPOTENCY_TTL_HOURS)
    try:
        session.execute(
            text(
                """
                INSERT INTO pos.idempotency_keys
                    (key, tenant_id, endpoint, request_hash, expires_at)
                VALUES (:key, :tid, :endpoint, :hash, :exp)
                """
            ),
            {
                "key": key,
                "tid": tenant_id,
                "endpoint": endpoint,
                "hash": request_hash,
                "exp": expires,
            },
        )
    except IntegrityError:
        session.rollback()
        return check_and_claim(session, key, tenant_id, endpoint, request_hash)

    return IdempotencyContext(key=key, request_hash=request_hash, replay=False)


def record_response(
    session: Session,
    key: str,
    response_status: int,
    response_body: dict[str, Any] | None,
) -> None:
    """Persist the response for a previously-claimed key."""
    session.execute(
        text(
            """
            UPDATE pos.idempotency_keys
               SET response_status = :st, response_body = :body
             WHERE key = :key
            """
        ),
        {"key": key, "st": response_status, "body": response_body},
    )


def idempotency_dependency(endpoint: str):
    """Return a FastAPI dependency that claims or replays an idempotency key.

    Usage::

        @router.post(
            "/foo",
            dependencies=[Depends(idempotency_dependency("POST /foo"))],
        )

    or, to access the context inside the handler::

        def handler(idem = Depends(idempotency_dependency("POST /foo"))):
            if idem.replay:
                return idem.cached_body
            ...
    """
    from datapulse.api.deps import get_tenant_session

    async def _dep(
        request: Request,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),  # noqa: B008
        session: Session = Depends(get_tenant_session),  # noqa: B008
    ) -> IdempotencyContext:
        body = await request.body()
        tenant_id = int(getattr(request.state, "tenant_id", 1))
        return check_and_claim(
            session=session,
            key=idempotency_key,
            tenant_id=tenant_id,
            endpoint=endpoint,
            request_hash=hash_body(body),
        )

    return _dep
