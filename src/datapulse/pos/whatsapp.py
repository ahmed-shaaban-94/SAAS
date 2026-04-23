"""WhatsApp receipt delivery — providers and helpers (#629).

The POS receipt-delivery flow is:

1. Cashier taps "Send via WhatsApp" on the checkout confirmation screen.
2. Route validates the phone number and auth/RLS context.
3. Service fetches the PDF receipt via ``PosService.get_receipt_pdf``.
4. Service hands the PDF to the configured :class:`WhatsAppProvider`.
5. Provider delivers via a BSP (Twilio / WhatsApp Cloud API).

The provider surface is intentionally narrow so we can swap Twilio for
WhatsApp Cloud API (or vice versa) without touching route or service code.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


class WhatsAppReceiptError(Exception):
    """Provider-layer error raised by :class:`WhatsAppProvider` implementations.

    Intentionally standalone (not a :class:`PosError`) so the provider module
    stays decoupled from POS domain exceptions. The service mixin catches
    this and re-raises as :class:`datapulse.pos.exceptions.WhatsAppDeliveryFailedError`
    so FastAPI returns 502 with a safe detail.

    Phone numbers are **never** embedded in the message — callers pass a
    hashed fingerprint via :func:`hash_phone` when logging.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class WhatsAppDeliveryResult:
    """Immutable result of a successful WhatsApp send.

    ``provider_message_id`` is opaque — each BSP uses a different id shape
    (Twilio SID, Cloud API WAMID), so the service logs but does not parse it.
    """

    provider_message_id: str


class WhatsAppProvider(Protocol):
    """Abstract delivery surface for a WhatsApp Business Solution Provider.

    Implementations must raise :class:`WhatsAppReceiptError` with a truthful
    ``retryable`` flag so the service can decide whether to retry once.
    """

    def send_receipt_pdf(
        self,
        phone_e164: str,
        pdf_bytes: bytes,
        caption: str,
    ) -> WhatsAppDeliveryResult: ...


def hash_phone(phone_e164: str) -> str:
    """Return a 16-char sha256 digest of ``phone_e164`` for safe logging.

    The prefix is wide enough to remain unique across one tenant's customer
    base and narrow enough that brute-force rainbow tables are expensive.
    Never log the raw phone.
    """
    digest = hashlib.sha256(phone_e164.encode("utf-8")).hexdigest()
    return digest[:16]


class MockWhatsAppProvider:
    """In-memory provider — captures every call, returns synthetic ids.

    Used in local dev, tests, and demo environments where we want the
    "sent via WhatsApp" UI state without hitting a real BSP. Each call
    returns a deterministic id (``mock-1``, ``mock-2``, ...) so assertions
    stay readable.

    ``fail_modes`` lets a test inject a scripted sequence of outcomes: each
    entry is either ``None`` (success) or a :class:`WhatsAppReceiptError`
    to raise on the next call. Beyond the list length, all calls succeed.
    """

    def __init__(
        self,
        *,
        fail_modes: list[WhatsAppReceiptError | None] | None = None,
    ) -> None:
        self.sent: list[tuple[str, bytes, str]] = []
        self._fail_modes = list(fail_modes or [])
        self._call_index = 0

    def send_receipt_pdf(
        self,
        phone_e164: str,
        pdf_bytes: bytes,
        caption: str,
    ) -> WhatsAppDeliveryResult:
        mode: WhatsAppReceiptError | None
        if self._call_index < len(self._fail_modes):
            mode = self._fail_modes[self._call_index]
        else:
            mode = None
        self._call_index += 1

        if mode is not None:
            raise mode

        self.sent.append((phone_e164, pdf_bytes, caption))
        return WhatsAppDeliveryResult(provider_message_id=f"mock-{len(self.sent)}")


class TwilioCloudApiProvider:
    """Twilio WhatsApp Business API provider — credential-holding stub.

    Constructor validates that credentials are present (so a misconfigured
    deployment fails loudly at startup rather than at first send).
    :meth:`send_receipt_pdf` raises :class:`NotImplementedError` until the
    live HTTP path lands in a follow-up PR; deployments that want a real
    provider today should keep ``whatsapp_receipt_provider`` at ``mock``.
    """

    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str,
    ) -> None:
        if not account_sid or not auth_token or not from_number:
            raise ValueError(
                "TwilioCloudApiProvider requires account_sid, auth_token, and from_number.",
            )
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number

    def send_receipt_pdf(
        self,
        phone_e164: str,
        pdf_bytes: bytes,
        caption: str,
    ) -> WhatsAppDeliveryResult:
        raise NotImplementedError(
            "TwilioCloudApiProvider is a stub — live HTTP delivery lands in a "
            "follow-up PR once sandbox credentials are provisioned. Use "
            "MockWhatsAppProvider in dev/test.",
        )
