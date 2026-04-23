"""Tests for POS WhatsApp receipt delivery (#629).

Covers:
- Phone hashing is deterministic and 16 hex chars.
- :class:`MockWhatsAppProvider` captures calls and replays scripted failures.
- :class:`TwilioCloudApiProvider` constructor rejects missing credentials.
- Service: feature off -> WhatsAppDisabledError.
- Service: invalid phone -> InvalidPhoneError.
- Service: happy path returns phone_hash + provider_message_id (raw phone never leaks).
- Service: retryable error retries exactly once and then succeeds.
- Service: non-retryable error surfaces immediately with no retry.
- Service: retryable error exhausts retries -> WhatsAppDeliveryFailedError.
- Route: rate-limit decorator is declared at 10/minute.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from datapulse.pos._service_whatsapp import WhatsAppReceiptMixin
from datapulse.pos.exceptions import (
    InvalidPhoneError,
    WhatsAppDeliveryFailedError,
    WhatsAppDisabledError,
)
from datapulse.pos.whatsapp import (
    MockWhatsAppProvider,
    TwilioCloudApiProvider,
    WhatsAppDeliveryResult,
    WhatsAppReceiptError,
    hash_phone,
)

_PHONE_RAW = "01198765432"
_PHONE_E164 = "+201198765432"
_PDF_BYTES = b"%PDF-1.4 mock"


class _ServiceUnderTest(WhatsAppReceiptMixin):
    """Minimal service that only exposes the mixin surface for testing."""

    def __init__(self, whatsapp: MockWhatsAppProvider | None) -> None:
        self._whatsapp = whatsapp

    def get_receipt_pdf(self, transaction_id: int, tenant_id: int) -> bytes:  # noqa: ARG002
        return _PDF_BYTES


# ---------------------------------------------------------------------------
# hash_phone
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hash_phone_is_deterministic_and_16_chars() -> None:
    h1 = hash_phone(_PHONE_E164)
    h2 = hash_phone(_PHONE_E164)
    assert h1 == h2
    assert len(h1) == 16
    assert all(c in "0123456789abcdef" for c in h1)


@pytest.mark.unit
def test_hash_phone_differs_per_number() -> None:
    assert hash_phone("+201198765432") != hash_phone("+201198765433")


# ---------------------------------------------------------------------------
# MockWhatsAppProvider
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mock_provider_captures_calls() -> None:
    provider = MockWhatsAppProvider()
    result = provider.send_receipt_pdf(_PHONE_E164, _PDF_BYTES, "Receipt #1")
    assert isinstance(result, WhatsAppDeliveryResult)
    assert result.provider_message_id == "mock-1"
    assert provider.sent == [(_PHONE_E164, _PDF_BYTES, "Receipt #1")]


@pytest.mark.unit
def test_mock_provider_replays_scripted_failures() -> None:
    provider = MockWhatsAppProvider(
        fail_modes=[
            WhatsAppReceiptError("boom", retryable=True),
            None,
        ],
    )
    with pytest.raises(WhatsAppReceiptError):
        provider.send_receipt_pdf(_PHONE_E164, _PDF_BYTES, "Receipt #1")
    result = provider.send_receipt_pdf(_PHONE_E164, _PDF_BYTES, "Receipt #1")
    assert result.provider_message_id == "mock-1"  # index counts successes only


# ---------------------------------------------------------------------------
# TwilioCloudApiProvider
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_twilio_provider_rejects_missing_credentials() -> None:
    with pytest.raises(ValueError):
        TwilioCloudApiProvider(account_sid="", auth_token="x", from_number="+1")
    with pytest.raises(ValueError):
        TwilioCloudApiProvider(account_sid="x", auth_token="", from_number="+1")
    with pytest.raises(ValueError):
        TwilioCloudApiProvider(account_sid="x", auth_token="x", from_number="")


@pytest.mark.unit
def test_twilio_provider_is_stub_until_wired() -> None:
    provider = TwilioCloudApiProvider(
        account_sid="sid",
        auth_token="token",
        from_number="+141555500100",
    )
    with pytest.raises(NotImplementedError):
        provider.send_receipt_pdf(_PHONE_E164, _PDF_BYTES, "Receipt #1")


# ---------------------------------------------------------------------------
# Service mixin — feature gating
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_service_feature_off_raises_disabled() -> None:
    service = _ServiceUnderTest(whatsapp=None)
    with pytest.raises(WhatsAppDisabledError):
        service.send_receipt_whatsapp(
            transaction_id=10,
            phone_raw=_PHONE_RAW,
            tenant_id=1,
        )


# ---------------------------------------------------------------------------
# Service mixin — phone validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_service_invalid_phone_raises_before_provider_call() -> None:
    provider = MockWhatsAppProvider()
    service = _ServiceUnderTest(whatsapp=provider)
    with pytest.raises(InvalidPhoneError):
        service.send_receipt_whatsapp(
            transaction_id=10,
            phone_raw="not-a-phone",
            tenant_id=1,
        )
    assert provider.sent == []  # provider never called


# ---------------------------------------------------------------------------
# Service mixin — happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_service_happy_path_returns_hash_and_provider_id() -> None:
    provider = MockWhatsAppProvider()
    service = _ServiceUnderTest(whatsapp=provider)

    response = service.send_receipt_whatsapp(
        transaction_id=42,
        phone_raw=_PHONE_RAW,
        tenant_id=1,
    )

    assert response["sent"] is True
    assert response["provider_message_id"] == "mock-1"
    assert response["phone_hash"] == hash_phone(_PHONE_E164)

    # Raw phone is never in the response — only the hash.
    assert _PHONE_RAW not in str(response)
    assert _PHONE_E164 not in str(response)

    # Provider received the E.164 form, not the raw cashier input.
    assert provider.sent == [(_PHONE_E164, _PDF_BYTES, "Receipt #42")]


# ---------------------------------------------------------------------------
# Service mixin — retry semantics
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_service_retries_once_on_retryable_error_then_succeeds() -> None:
    provider = MockWhatsAppProvider(
        fail_modes=[WhatsAppReceiptError("transient", retryable=True)],
    )
    service = _ServiceUnderTest(whatsapp=provider)

    response = service.send_receipt_whatsapp(
        transaction_id=7,
        phone_raw=_PHONE_RAW,
        tenant_id=1,
    )

    assert response["sent"] is True
    assert response["provider_message_id"] == "mock-1"
    assert len(provider.sent) == 1  # one successful send after one failure


@pytest.mark.unit
def test_service_does_not_retry_non_retryable_error() -> None:
    provider = MockWhatsAppProvider(
        fail_modes=[
            WhatsAppReceiptError("bad number", retryable=False),
            None,  # would succeed if we retried — we must NOT reach this
        ],
    )
    service = _ServiceUnderTest(whatsapp=provider)

    with pytest.raises(WhatsAppDeliveryFailedError):
        service.send_receipt_whatsapp(
            transaction_id=7,
            phone_raw=_PHONE_RAW,
            tenant_id=1,
        )
    assert provider.sent == []  # non-retryable -> single attempt


@pytest.mark.unit
def test_service_surfaces_delivery_failed_after_exhausted_retries() -> None:
    provider = MockWhatsAppProvider(
        fail_modes=[
            WhatsAppReceiptError("transient 1", retryable=True),
            WhatsAppReceiptError("transient 2", retryable=True),
        ],
    )
    service = _ServiceUnderTest(whatsapp=provider)

    with pytest.raises(WhatsAppDeliveryFailedError) as excinfo:
        service.send_receipt_whatsapp(
            transaction_id=7,
            phone_raw=_PHONE_RAW,
            tenant_id=1,
        )
    # The last failure's reason is surfaced via .reason for logging + triage.
    assert excinfo.value.reason == "transient 2"
    assert provider.sent == []  # both attempts failed


# ---------------------------------------------------------------------------
# Service mixin — RLS delegation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_service_delegates_receipt_fetch_with_tenant_id() -> None:
    provider = MockWhatsAppProvider()
    service = _ServiceUnderTest(whatsapp=provider)
    service.get_receipt_pdf = Mock(return_value=_PDF_BYTES)  # type: ignore[method-assign]

    service.send_receipt_whatsapp(
        transaction_id=100,
        phone_raw=_PHONE_RAW,
        tenant_id=42,
    )

    service.get_receipt_pdf.assert_called_once_with(100, 42)


# ---------------------------------------------------------------------------
# Route — rate-limit declaration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_route_declares_10_per_minute_rate_limit() -> None:
    """Regression guard: #629 AC mandates a rate limit consistent with email (10/min)."""
    from datapulse.api.routes import _pos_receipts

    source = _pos_receipts.__file__
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    assert "/receipts/{transaction_id}/whatsapp" in text
    assert 'limiter.limit("10/minute")' in text
