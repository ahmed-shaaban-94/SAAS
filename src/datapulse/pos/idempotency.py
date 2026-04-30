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

from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    PosConflictError,
    PosError,
    PosInternalError,
    PosNotFoundError,
    PosValidationError,
    ShiftNotOpenError,
    TerminalNotActiveError,
    VoidNotAllowedError,
    WhatsAppDeliveryFailedError,
    WhatsAppDisabledError,
)

IDEMPOTENCY_TTL_HOURS: int = 168
PROVISIONAL_TTL_HOURS: int = 72


@dataclass(frozen=True)
class IdempotencyContext:
    """Outcome of check_and_claim for a particular Idempotency-Key."""

    key: str
    tenant_id: int
    endpoint: str
    request_hash: str
    replay: bool
    cached_status: int | None = None
    cached_body: dict[str, Any] | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def hash_body(body: bytes) -> str:
    """SHA-256 hex digest of the raw request body."""
    return hashlib.sha256(body).hexdigest()


def _metric(event: str, endpoint: str, status_code: int | None = None) -> None:
    from datapulse.metrics import pos_idempotency_events_total

    pos_idempotency_events_total.labels(
        event=event,
        endpoint=endpoint,
        status=str(status_code if status_code is not None else "none"),
    ).inc()


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
            SELECT endpoint, request_hash, response_status, response_body, expires_at
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
            if row["endpoint"] != endpoint:
                _metric("conflict_endpoint", endpoint, status.HTTP_409_CONFLICT)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key reuse across endpoints.",
                )
            if row["request_hash"] != request_hash:
                _metric("conflict_hash", endpoint, status.HTTP_409_CONFLICT)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key reuse with different request body.",
                )
            if row["response_status"] is None:
                _metric("pending", endpoint, status.HTTP_409_CONFLICT)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key request is still processing.",
                )
            _metric("replay", endpoint, int(row["response_status"]))
            return IdempotencyContext(
                key=key,
                tenant_id=tenant_id,
                endpoint=endpoint,
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

    return IdempotencyContext(
        key=key,
        tenant_id=tenant_id,
        endpoint=endpoint,
        request_hash=request_hash,
        replay=False,
    )


def record_response(
    session: Session,
    key: str,
    response_status: int,
    response_body: dict[str, Any] | None,
    *,
    tenant_id: int,
) -> None:
    """Persist the response for a previously-claimed key."""
    session.execute(
        text(
            """
            UPDATE pos.idempotency_keys
               SET response_status = :st, response_body = :body
             WHERE key = :key
               AND tenant_id = :tenant_id
            """
        ),
        {
            "key": key,
            "tenant_id": tenant_id,
            "st": response_status,
            "body": response_body,
        },
    )


def raise_for_replayed_error(idem: IdempotencyContext) -> None:
    """Raise the cached HTTP error for a replayed failed idempotent request."""
    if idem.replay and idem.cached_status is not None and idem.cached_status >= 400:
        detail = "idempotent request failed"
        if isinstance(idem.cached_body, dict):
            detail = idem.cached_body.get("detail", detail)
        raise HTTPException(status_code=idem.cached_status, detail=detail)


def pos_error_status(exc: PosError) -> int:
    """Mirror production POS exception handlers for idempotency storage."""
    if isinstance(exc, PosNotFoundError):
        return exc.http_status
    if isinstance(
        exc,
        (
            InsufficientStockError,
            PosConflictError,
            ShiftNotOpenError,
            TerminalNotActiveError,
            VoidNotAllowedError,
        ),
    ):
        return 409
    if isinstance(exc, PharmacistVerificationRequiredError):
        return 403
    if isinstance(exc, WhatsAppDisabledError):
        return 503
    if isinstance(exc, WhatsAppDeliveryFailedError):
        return 502
    if isinstance(exc, PosValidationError):
        return 400
    if isinstance(exc, PosInternalError):
        return 500
    return 400


def record_idempotent_success(
    session: Session,
    idem: IdempotencyContext,
    status_code: int,
    response_body: dict[str, Any] | None,
) -> None:
    """Persist and commit a successful idempotent response."""
    record_response(
        session,
        idem.key,
        status_code,
        response_body,
        tenant_id=idem.tenant_id,
    )
    _metric("success", idem.endpoint, status_code)
    session.commit()


def record_idempotent_error(
    session: Session,
    idem: IdempotencyContext,
    *,
    status_code: int,
    detail: object,
) -> None:
    """Rollback business work, then persist and commit a replayable error response."""
    session.rollback()
    body = {"detail": detail}
    expires = _now() + timedelta(hours=IDEMPOTENCY_TTL_HOURS)
    session.execute(
        text("SET LOCAL app.tenant_id = :tid"),
        {"tid": str(idem.tenant_id)},
    )
    session.execute(
        text(
            """
            INSERT INTO pos.idempotency_keys
                (key, tenant_id, endpoint, request_hash, response_status, response_body, expires_at)
            VALUES (:key, :tenant_id, :endpoint, :hash, :st, :body, :exp)
            ON CONFLICT (tenant_id, key) DO UPDATE
               SET response_status = EXCLUDED.response_status,
                   response_body = EXCLUDED.response_body,
                   expires_at = GREATEST(pos.idempotency_keys.expires_at, EXCLUDED.expires_at)
             WHERE pos.idempotency_keys.endpoint = EXCLUDED.endpoint
               AND pos.idempotency_keys.request_hash = EXCLUDED.request_hash
            """
        ),
        {
            "key": idem.key,
            "tenant_id": idem.tenant_id,
            "endpoint": idem.endpoint,
            "hash": idem.request_hash,
            "st": status_code,
            "body": body,
            "exp": expires,
        },
    )
    _metric("error", idem.endpoint, status_code)
    session.commit()


def record_idempotent_exception(
    session: Session,
    idem: IdempotencyContext,
    exc: HTTPException | PosError,
) -> None:
    """Persist a replayable response for expected route/business exceptions."""
    if isinstance(exc, HTTPException):
        record_idempotent_error(
            session,
            idem,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return
    record_idempotent_error(
        session,
        idem,
        status_code=pos_error_status(exc),
        detail=exc.message,
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
    from datapulse.core.auth import get_current_user, get_tenant_session

    async def _dep(
        request: Request,
        user: dict = Depends(get_current_user),  # noqa: B008
        idempotency_key: str = Header(..., alias="Idempotency-Key"),  # noqa: B008
        session: Session = Depends(get_tenant_session),  # noqa: B008
    ) -> IdempotencyContext:
        body = await request.body()
        # Tenant context comes from the JWT claims via CurrentUser, with
        # ``request.state.tenant_id`` retained as a defensive fallback for
        # any future middleware that pre-populates it. Silently falling back
        # to tenant_id=1 would let one tenant's client replay another
        # tenant's cached response, so we 401 if neither source resolves.
        # Catches: missing key (KeyError on user["tenant_id"]), attribute
        # missing (AttributeError on request.state.tenant_id), attribute is
        # None (TypeError on int(None)), attribute is non-numeric string
        # (ValueError on int("")).
        raw_tid: object = user.get("tenant_id")  # type: ignore[union-attr]
        if raw_tid in (None, ""):
            raw_tid = getattr(request.state, "tenant_id", None)
        try:
            tenant_id = int(raw_tid)  # type: ignore[call-overload]
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=401,
                detail="request missing tenant context",
            ) from exc
        return check_and_claim(
            session=session,
            key=idempotency_key,
            tenant_id=tenant_id,
            endpoint=endpoint,
            request_hash=hash_body(body),
        )

    return _dep
