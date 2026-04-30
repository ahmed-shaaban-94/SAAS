"""POS receipt routes — PDF, thermal, and email delivery (B4).

Sub-router for ``pos.py`` facade (issue #543).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import Response
from pydantic import BaseModel

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    SessionDep,
    _receipt_email_idempotency_dep,
    _receipt_whatsapp_idempotency_dep,
    _tenant_id_of,
)
from datapulse.logging import get_logger
from datapulse.pos.exceptions import PosError
from datapulse.pos.idempotency import (
    IdempotencyContext,
    raise_for_replayed_error,
    record_idempotent_exception,
    record_idempotent_success,
)
from datapulse.pos.models import EmailReceiptRequest
from datapulse.rbac.dependencies import require_permission

log = get_logger(__name__)

router = APIRouter()


@router.get(
    "/receipts/{transaction_id}",
    dependencies=[Depends(require_permission("pos:receipt:read"))],
)
@limiter.limit("60/minute")
def get_receipt_pdf(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> Response:
    """Return the PDF receipt for a completed transaction."""
    content = service.get_receipt_pdf(transaction_id, _tenant_id_of(user))
    return Response(content=content, media_type="application/pdf")


@router.get(
    "/receipts/{transaction_id}/thermal",
    dependencies=[Depends(require_permission("pos:receipt:read"))],
)
@limiter.limit("60/minute")
def get_receipt_thermal(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    service: ServiceDep,
    user: CurrentUser,
) -> Response:
    """Return the raw ESC/POS thermal receipt bytes."""
    content = service.get_receipt_thermal(transaction_id, _tenant_id_of(user))
    return Response(content=content, media_type="application/octet-stream")


@router.post(
    "/receipts/{transaction_id}/email",
    dependencies=[Depends(require_permission("pos:receipt:send"))],
)
@limiter.limit("10/minute")
def send_receipt_email(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: EmailReceiptRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_receipt_email_idempotency_dep)],
) -> dict:
    """Send the PDF receipt to the given email address (stub — email delivery in Phase 2)."""
    if idem.replay:
        raise_for_replayed_error(idem)
        return idem.cached_body or {"sent": True, "email": body.email}
    try:
        _ = service.get_receipt_pdf(transaction_id, _tenant_id_of(user))
        response = {"sent": True, "email": body.email}
        log.info("pos.receipt.email_queued", transaction_id=transaction_id, email=body.email)
    except (HTTPException, PosError) as exc:
        record_idempotent_exception(db_session, idem, exc)
        raise
    record_idempotent_success(db_session, idem, 200, response)
    return response


class _WhatsAppReceiptRequest(BaseModel):
    phone: str


@router.post(
    "/receipts/{transaction_id}/whatsapp",
    dependencies=[Depends(require_permission("pos:receipt:send"))],
)
@limiter.limit("10/minute")
def send_receipt_whatsapp(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: _WhatsAppReceiptRequest,
    service: ServiceDep,
    user: CurrentUser,
    db_session: SessionDep,
    idem: Annotated[IdempotencyContext, Depends(_receipt_whatsapp_idempotency_dep)],
) -> dict:
    """Send the PDF receipt to the given phone via WhatsApp (#629).

    Feature-flag gated. When disabled the service raises
    :class:`WhatsAppDisabledError` -> 503 so the UI can fall back to print.
    The raw phone is never logged — only a truncated sha256 hash.
    """
    if idem.replay:
        raise_for_replayed_error(idem)
        return idem.cached_body or {"sent": True}
    try:
        response = service.send_receipt_whatsapp(
            transaction_id,
            body.phone,
            _tenant_id_of(user),
        )
    except (HTTPException, PosError) as exc:
        record_idempotent_exception(db_session, idem, exc)
        raise
    record_idempotent_success(db_session, idem, 200, response)
    return response
