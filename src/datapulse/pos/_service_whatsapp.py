"""WhatsApp receipt delivery — service mixin (#629).

Adds ``send_receipt_whatsapp`` to :class:`PosService`. The mixin treats
the WhatsApp provider as an optional collaborator: when no provider is
wired (feature flag off) any call raises :class:`WhatsAppDisabledError`
so the route returns 503 and the UI can fall back to "Print instead".

The mixin enforces three invariants documented by issue #629:

* Phone numbers are normalized to E.164 (via the shared
  :func:`normalize_egyptian_phone`) and never logged raw — only
  :func:`hash_phone`.
* The provider is retried **exactly once** on a retryable error; a
  non-retryable error or a second failure surfaces as
  :class:`WhatsAppDeliveryFailedError` for the cashier to see.
* Receipt fetch is delegated to :meth:`CatalogMixin.get_receipt_pdf`,
  which already enforces tenant-scoped RLS — the mixin does not
  duplicate that guard.
"""

from __future__ import annotations

from typing import Any

from datapulse.logging import get_logger
from datapulse.pos.exceptions import (
    InvalidPhoneError,
    WhatsAppDeliveryFailedError,
    WhatsAppDisabledError,
)
from datapulse.pos.phone import normalize_egyptian_phone
from datapulse.pos.whatsapp import (
    WhatsAppDeliveryResult,
    WhatsAppProvider,
    WhatsAppReceiptError,
    hash_phone,
)

log = get_logger(__name__)

_MAX_RETRIES = 1


class WhatsAppReceiptMixin:
    """Provides :meth:`send_receipt_whatsapp` on :class:`PosService`.

    Collaborators expected from the composed service:

    * ``self._whatsapp`` — optional :class:`WhatsAppProvider`
    * ``self.get_receipt_pdf`` — inherited from :class:`CatalogMixin`
    """

    _whatsapp: WhatsAppProvider | None

    def send_receipt_whatsapp(
        self,
        transaction_id: int,
        phone_raw: str,
        tenant_id: int,
    ) -> dict[str, Any]:
        """Send the PDF receipt for ``transaction_id`` to the given phone.

        Returns a dict with ``sent``, ``phone_hash``, and
        ``provider_message_id`` — suitable as a JSON response body.

        Raises:
            WhatsAppDisabledError: feature flag off or no provider wired.
            InvalidPhoneError: ``phone_raw`` fails E.164 normalization.
            WhatsAppDeliveryFailedError: provider failed after retry.
        """
        if self._whatsapp is None:
            raise WhatsAppDisabledError()

        phone_e164 = normalize_egyptian_phone(phone_raw)
        if phone_e164 is None:
            raise InvalidPhoneError(
                "Invalid phone number. Expected Egyptian mobile in E.164, "
                "11-digit, or 12-digit form.",
            )
        phone_hash = hash_phone(phone_e164)

        pdf_bytes = self.get_receipt_pdf(transaction_id, tenant_id)  # type: ignore[attr-defined]
        caption = f"Receipt #{transaction_id}"

        last_error: WhatsAppReceiptError | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                result: WhatsAppDeliveryResult = self._whatsapp.send_receipt_pdf(
                    phone_e164,
                    pdf_bytes,
                    caption,
                )
            except WhatsAppReceiptError as exc:
                last_error = exc
                log.warning(
                    "pos.receipt.whatsapp_attempt_failed",
                    transaction_id=transaction_id,
                    phone_hash=phone_hash,
                    attempt=attempt,
                    retryable=exc.retryable,
                )
                if not exc.retryable or attempt >= _MAX_RETRIES:
                    break
                continue
            else:
                log.info(
                    "pos.receipt.whatsapp_sent",
                    transaction_id=transaction_id,
                    phone_hash=phone_hash,
                    provider_message_id=result.provider_message_id,
                    attempts=attempt + 1,
                )
                return {
                    "sent": True,
                    "phone_hash": phone_hash,
                    "provider_message_id": result.provider_message_id,
                }

        reason = str(last_error) if last_error else "unknown provider error"
        raise WhatsAppDeliveryFailedError(reason)
