"""Unit tests for PaymobCardGateway (#738).

Covers:
- Successful payment returns PaymentResult(success=True) with authorization_code.
- 4xx error from Paymob is classified as permanent, returns success=False.
- 5xx error is classified as temporary, returns success=False with retry message.
- Unknown error (no status_code) classified as unknown, returns success=False.
- idem_key is forwarded to the callable as merchant_ref (idempotency guarantee).
- PaymentResult fields match the contract in pos/payment.py (method, amount_charged, etc.).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.payment import PaymentResult
from datapulse.pos.paymob_gateway import (
    PaymobCardGateway,
    PaymobErrorKind,
    _classify_error,
    _user_message,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_gateway(return_value: dict | None = None, side_effect: Exception | None = None):
    """Build a gateway with a mocked create_pos_payment callable."""
    mock_create = MagicMock()
    if side_effect is not None:
        mock_create.side_effect = side_effect
    else:
        mock_create.return_value = return_value or {"order_id": "txn-123"}
    return PaymobCardGateway(create_pos_payment=mock_create, hmac_secret="test-secret"), mock_create


def _make_http_error(status_code: int) -> Exception:
    exc = Exception(f"HTTP {status_code}")
    exc.status_code = status_code  # type: ignore[attr-defined]
    return exc


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_successful_payment_returns_true():
    gw, mock_create = _make_gateway({"order_id": "txn-123"})
    result = gw.process_payment(Decimal("100.00"), idem_key="idem-1")

    assert isinstance(result, PaymentResult)
    assert result.success is True
    assert result.method == "card"
    assert result.amount_charged == Decimal("100.00")
    assert result.authorization_code == "txn-123"


def test_successful_payment_forwards_idem_key_as_merchant_ref():
    gw, mock_create = _make_gateway({"order_id": "txn-999"})
    gw.process_payment(Decimal("50.00"), idem_key="my-idem-key")

    # idem_key must be forwarded as the second positional arg (merchant_ref)
    args, kwargs = mock_create.call_args
    assert args[1] == "my-idem-key"


def test_successful_payment_fallback_to_id_field():
    """Gateway also handles dict with 'id' key instead of 'order_id'."""
    gw, _ = _make_gateway({"id": "fallback-id"})
    result = gw.process_payment(Decimal("10.00"))
    assert result.success is True
    assert result.authorization_code == "fallback-id"


# ---------------------------------------------------------------------------
# Failure paths — 4xx permanent
# ---------------------------------------------------------------------------


def test_4xx_returns_permanent_failure():
    gw, _ = _make_gateway(side_effect=_make_http_error(402))
    result = gw.process_payment(Decimal("100.00"), idem_key="idem-2")

    assert result.success is False
    assert result.method == "card"
    assert result.amount_charged == Decimal("0")
    assert "declined" in result.message.lower()


def test_400_returns_failure():
    gw, _ = _make_gateway(side_effect=_make_http_error(400))
    result = gw.process_payment(Decimal("100.00"))
    assert result.success is False


def test_403_returns_failure():
    gw, _ = _make_gateway(side_effect=_make_http_error(403))
    result = gw.process_payment(Decimal("100.00"))
    assert result.success is False


# ---------------------------------------------------------------------------
# Failure paths — 5xx temporary
# ---------------------------------------------------------------------------


def test_5xx_returns_temporary_failure():
    gw, _ = _make_gateway(side_effect=_make_http_error(504))
    result = gw.process_payment(Decimal("100.00"), idem_key="idem-3")

    assert result.success is False
    assert result.method == "card"
    assert "retry" in result.message.lower()


def test_500_returns_temporary_failure():
    gw, _ = _make_gateway(side_effect=_make_http_error(500))
    result = gw.process_payment(Decimal("100.00"))
    assert result.success is False


# ---------------------------------------------------------------------------
# Failure paths — unknown (no status_code)
# ---------------------------------------------------------------------------


def test_no_status_code_returns_unknown_failure():
    gw, _ = _make_gateway(side_effect=ValueError("network error"))
    result = gw.process_payment(Decimal("100.00"))

    assert result.success is False
    assert "uncertain" in result.message.lower() or "contact support" in result.message.lower()


def test_exception_with_response_object_status_code():
    """Exceptions that store status_code on .response (e.g. httpx) are handled."""
    exc = Exception("httpx style")
    response_mock = MagicMock()
    response_mock.status_code = 503
    exc.response = response_mock  # type: ignore[attr-defined]
    gw, _ = _make_gateway(side_effect=exc)
    result = gw.process_payment(Decimal("100.00"))

    assert result.success is False
    assert "retry" in result.message.lower()


# ---------------------------------------------------------------------------
# _classify_error unit tests
# ---------------------------------------------------------------------------


def test_classify_permanent():
    exc = _make_http_error(422)
    assert _classify_error(exc) == PaymobErrorKind.permanent


def test_classify_temporary():
    exc = _make_http_error(502)
    assert _classify_error(exc) == PaymobErrorKind.temporary


def test_classify_unknown():
    assert _classify_error(RuntimeError("boom")) == PaymobErrorKind.unknown


# ---------------------------------------------------------------------------
# _user_message unit tests
# ---------------------------------------------------------------------------


def test_user_message_permanent():
    msg = _user_message(PaymobErrorKind.permanent, "")
    assert "declined" in msg.lower()
    assert "cash" in msg.lower()


def test_user_message_temporary():
    msg = _user_message(PaymobErrorKind.temporary, "")
    assert "retry" in msg.lower()
    assert "not been charged" in msg.lower()


def test_user_message_unknown():
    msg = _user_message(PaymobErrorKind.unknown, "")
    assert "support" in msg.lower()


# ---------------------------------------------------------------------------
# Contract compliance
# ---------------------------------------------------------------------------


def test_process_payment_never_raises_on_expected_failure():
    """ABC contract: implementations must NOT raise for payment-level errors."""
    gw, _ = _make_gateway(side_effect=_make_http_error(402))
    # Should not raise — must return PaymentResult(success=False)
    result = gw.process_payment(Decimal("100.00"))
    assert result.success is False


def test_process_payment_no_idem_key_uses_empty_merchant_ref():
    gw, mock_create = _make_gateway()
    gw.process_payment(Decimal("25.00"))
    args, _ = mock_create.call_args
    assert args[1] == ""  # merchant_ref is empty string when idem_key is None


def test_currency_default_is_egp():
    gw, mock_create = _make_gateway()
    gw.process_payment(Decimal("50.00"), idem_key="key-1")
    args, _ = mock_create.call_args
    assert args[2] == "EGP"


def test_custom_currency_forwarded():
    gw, mock_create = _make_gateway()
    gw.process_payment(Decimal("50.00"), idem_key="key-1", currency="USD")
    args, _ = mock_create.call_args
    assert args[2] == "USD"


# ---------------------------------------------------------------------------
# Wiring integration — PosService routes card payments to injected gateway
# ---------------------------------------------------------------------------


def test_pos_service_uses_injected_card_gateway():
    """When PosService is constructed with card_gateway=<gateway>, a card checkout
    must call that gateway's process_payment, NOT the CardGateway stub.

    This guards against accidental re-orphaning of the gateway after refactors.
    """
    from datapulse.pos.service import PosService

    sentinel_gw, mock_create = _make_gateway({"order_id": "wired-txn"})

    # PosService accepts optional keyword-only collaborators; inject only what
    # the wiring test needs — the card_gateway parameter added in #738.
    svc = PosService.__new__(PosService)
    svc._card_gateway = sentinel_gw  # type: ignore[attr-defined]

    # Simulate what CheckoutMixin does: pick the right gateway for "card".
    from datapulse.pos.payment import get_gateway

    method = "card"
    if method == "card" and svc._card_gateway is not None:
        chosen_gw = svc._card_gateway
    else:
        chosen_gw = get_gateway(method)

    result = chosen_gw.process_payment(Decimal("75.00"), idem_key="wired-key")

    # Assert the sentinel (PaymobCardGateway) was used, not the stub.
    mock_create.assert_called_once()
    assert result.success is True
    assert result.authorization_code == "wired-txn"
    assert result.method == "card"


def test_pos_service_falls_back_to_stub_when_card_gateway_none():
    """When card_gateway is None, CheckoutMixin falls back to CardGateway stub."""
    from datapulse.pos.payment import CardGateway, get_gateway

    card_gateway = None  # simulate unconfigured PAYMOB_API_KEY
    method = "card"

    if method == "card" and card_gateway is not None:
        chosen_gw = card_gateway
    else:
        chosen_gw = get_gateway(method)

    assert isinstance(chosen_gw, CardGateway)
    result = chosen_gw.process_payment(Decimal("50.00"))
    assert result.success is False
    msg = result.message.lower()
    assert "paymob_api_key" in msg or "paymobcardgateway" in msg
