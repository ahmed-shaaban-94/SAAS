"""PaymobCardGateway — bridges PaymentGateway contract to Paymob API (#738).

Design
------
* Accepts a ``create_pos_payment`` callable so the gateway has **no direct
  import from** ``datapulse.billing`` — wiring is done in ``api/deps.py``
  (dependency-injection, not layer import).
* Follows the ``PaymentGateway`` contract: sync, returns ``PaymentResult`` for
  both success and expected failure; never raises for payment-level errors.
* Idempotency: the ``idem_key`` kwarg is forwarded as Paymob's
  ``merchant_order_id``, so Paymob-side deduplication prevents double-charges
  on retries.  Callers should also wrap the endpoint with
  ``pos.idempotency.idempotency_dependency`` for full request-level dedupe.

Error contract (surfaced via structlog ``error_kind`` field):
* ``temporary``  — network timeout or 5xx — safe to retry with the same key.
* ``permanent``  — declined / fraud block / 4xx — show user message, no retry.
* ``unknown``    — ambiguous outcome — surface to ops, manual reconcile.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from enum import StrEnum
from typing import Any

import structlog

from datapulse.pos.payment import PaymentGateway, PaymentResult

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Error-kind enum (not an exception — used purely for logging / observability)
# ---------------------------------------------------------------------------


class PaymobErrorKind(StrEnum):
    """Classification of a Paymob call failure — shapes retry strategy."""

    temporary = "temporary"  # network/5xx — safe to retry with same idem_key
    permanent = "permanent"  # declined/4xx — show user message, do not retry
    unknown = "unknown"  # unclear — surface to ops, manual reconcile


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------


class PaymobCardGateway(PaymentGateway):
    """Card payment gateway that delegates to Paymob's API via DI callable.

    Args:
        create_pos_payment:
            Callable with signature
            ``(amount: Decimal, merchant_ref: str, currency: str) -> dict``
            that returns a dict with at least an ``"order_id"`` key.
            Must be provided from ``api/deps.py``; never import billing here.
        hmac_secret:
            Paymob HMAC secret, used only for webhook verification helpers.
            Not consumed in ``process_payment`` itself.
    """

    def __init__(
        self,
        create_pos_payment: Callable[[Decimal, str, str], dict[str, Any]],
        hmac_secret: str = "",
    ) -> None:
        self._create_pos_payment = create_pos_payment
        self._hmac_secret = hmac_secret

    # ------------------------------------------------------------------
    # PaymentGateway contract
    # ------------------------------------------------------------------

    def process_payment(
        self,
        amount: Decimal,
        *,
        tendered: Decimal | None = None,
        insurance_no: str | None = None,
        card_token: str | None = None,
        idem_key: str | None = None,
        currency: str = "EGP",
        **kwargs: Any,
    ) -> PaymentResult:
        """Process a card payment for ``amount`` via Paymob.

        ``idem_key`` is forwarded as ``merchant_order_id`` so Paymob-side
        deduplication prevents double-charges on retry storms.

        Returns ``PaymentResult(success=True)`` on success.
        Returns ``PaymentResult(success=False)`` on expected failures
        (declined, timeout, fraud block) — never raises for those cases,
        matching the ``PaymentGateway`` contract.

        ``structlog`` records ``error_kind`` (temporary/permanent/unknown)
        so dashboards and alerting can distinguish transient vs permanent
        failures without parsing message strings.
        """
        merchant_ref = idem_key or ""
        log = logger.bind(
            gateway="paymob",
            idem_key=idem_key,
            amount=str(amount),
            currency=currency,
        )

        try:
            result = self._create_pos_payment(amount, merchant_ref, currency)
            order_id = str(result.get("order_id") or result.get("id") or "")
            log.info("pos.payment.paymob.success", order_id=order_id)
            return PaymentResult(
                success=True,
                method="card",
                amount_charged=amount,
                authorization_code=order_id,
                message="Card payment accepted via Paymob",
            )
        except Exception as exc:
            kind = _classify_error(exc)
            log.error(
                "pos.payment.paymob.error",
                error_kind=kind.value,
                error=str(exc),
            )
            return PaymentResult(
                success=False,
                method="card",
                amount_charged=Decimal("0"),
                message=_user_message(kind, str(exc)),
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_error(exc: Exception) -> PaymobErrorKind:
    """Derive error kind from HTTP status code attached to the exception."""
    status_code: int | None = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        if response is not None:
            status_code = getattr(response, "status_code", None)
    if status_code is not None:
        if 400 <= status_code < 500:
            return PaymobErrorKind.permanent
        if status_code >= 500:
            return PaymobErrorKind.temporary
    return PaymobErrorKind.unknown


def _user_message(kind: PaymobErrorKind, raw: str) -> str:
    if kind == PaymobErrorKind.permanent:
        return (
            "Your card payment was declined by the payment provider. "
            "Please try a different card or use cash."
        )
    if kind == PaymobErrorKind.temporary:
        return (
            "The card payment gateway is temporarily unavailable. "
            "Please retry — your card has not been charged."
        )
    # unknown
    return (
        "Card payment outcome is uncertain. "
        "Please contact support and quote your transaction reference."
    )
