"""POS receipt routes — PDF, thermal, and email delivery (B4).

Sub-router for ``pos.py`` facade (issue #543).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Request
from fastapi.responses import Response
from pydantic import BaseModel

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    _tenant_id_of,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

router = APIRouter()


@router.get("/receipts/{transaction_id}")
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


@router.get("/receipts/{transaction_id}/thermal")
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


class _EmailReceiptRequest(BaseModel):
    email: str


@router.post("/receipts/{transaction_id}/email")
@limiter.limit("10/minute")
def send_receipt_email(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: _EmailReceiptRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> dict:
    """Send the PDF receipt to the given email address (stub — email delivery in Phase 2)."""
    _ = service.get_receipt_pdf(transaction_id, _tenant_id_of(user))
    log.info("pos.receipt.email_queued", transaction_id=transaction_id, email=body.email)
    return {"sent": True, "email": body.email}


class _WhatsAppReceiptRequest(BaseModel):
    phone: str


@router.post("/receipts/{transaction_id}/whatsapp")
@limiter.limit("10/minute")
def send_receipt_whatsapp(
    request: Request,
    transaction_id: Annotated[int, Path(ge=1)],
    body: _WhatsAppReceiptRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> dict:
    """Send the PDF receipt to the given phone via WhatsApp (#629).

    Feature-flag gated. When disabled the service raises
    :class:`WhatsAppDisabledError` -> 503 so the UI can fall back to print.
    The raw phone is never logged — only a truncated sha256 hash.
    """
    return service.send_receipt_whatsapp(
        transaction_id,
        body.phone,
        _tenant_id_of(user),
    )
