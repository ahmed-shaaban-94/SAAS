"""Paymob payment gateway client — EGP payment provider (issue #604).

Implements the PaymentProvider Protocol using Paymob's Accept API:
  Step 1: POST /api/auth/tokens          → auth token
  Step 2: POST /api/ecommerce/orders     → order_id
  Step 3: POST /api/acceptance/payment_keys → payment_token
  Step 4: redirect to Paymob iFrame with payment_token

Webhook HMAC: sort notification fields, concatenate values, HMAC-SHA512
with the HMAC_SECRET from Paymob dashboard.

Amounts are in *piastres* (1 EGP = 100 piastres), matching PlanLimits.price_egp.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
import structlog

from datapulse.billing.models import WebhookResult

logger = structlog.get_logger()

_BASE = "https://accept.paymob.com/api"

# Fields used for HMAC calculation as documented by Paymob.
_HMAC_FIELDS = [
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order",
    "owner",
    "pending",
    "source_data.pan",
    "source_data.sub_type",
    "source_data.type",
    "success",
]


@dataclass
class _PaymobSession:
    """Minimal checkout-session shim with a `.url` attribute (mirrors Stripe)."""

    url: str
    order_id: str = ""
    payment_token: str = ""


class PaymobClient:
    """PaymentProvider implementation for Paymob (EGP)."""

    name = "paymob"
    currencies: frozenset[str] = frozenset({"EGP"})

    def __init__(
        self,
        api_key: str,
        integration_id: str,
        iframe_id: str,
        hmac_secret: str,
    ) -> None:
        self._api_key = api_key
        self._integration_id = integration_id
        self._iframe_id = iframe_id
        self._hmac_secret = hmac_secret

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._integration_id and self._iframe_id)

    # ── PaymentProvider Protocol ─────────────────────────────────────────────

    def create_customer(self, *, email: str, name: str, metadata: dict) -> dict:
        """Paymob doesn't have a persistent customer object — return an echo dict."""
        return {"email": email, "name": name, "id": f"paymob_{metadata.get('tenant_id', 'x')}"}

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> _PaymobSession:
        """Build a Paymob iframe checkout URL.

        ``price_id`` is a plan key (e.g. ``"pro"``) for EGP flow rather than
        a Stripe price ID.  Amount is looked up from ``PlanLimits.price_egp``.
        """
        from datapulse.billing.plans import get_plan_limits

        limits = get_plan_limits(price_id)
        amount_piastres = limits.price_egp

        # Encode tenant_id + plan in merchant_order_id so webhooks can resolve both.
        # Format: "paymob_<tenant_id>:<plan_key>" e.g. "paymob_42:pro"
        merchant_ref = f"{customer_id}:{price_id}"
        auth_token = self._auth_token()
        order_id = self._register_order(auth_token, amount_piastres, merchant_ref)
        payment_token = self._payment_key(auth_token, order_id, amount_piastres)

        iframe_url = (
            f"https://accept.paymob.com/api/acceptance/iframes/{self._iframe_id}"
            f"?payment_token={payment_token}"
        )
        logger.info("paymob_checkout_created", order_id=order_id, plan=price_id)
        return _PaymobSession(url=iframe_url, order_id=order_id, payment_token=payment_token)

    def create_portal_session(self, *, customer_id: str, return_url: str) -> _PaymobSession:
        """Paymob has no hosted portal — return a no-op with the return_url."""
        return _PaymobSession(url=return_url)

    def construct_webhook_event(self, payload: bytes, sig_header: str, webhook_secret: str) -> dict:
        """Verify Paymob HMAC and return the parsed notification data."""
        data: dict = json.loads(payload)
        calculated = self._calc_hmac(data.get("obj", {}), webhook_secret)
        if not hmac.compare_digest(calculated, sig_header):
            raise ValueError("Paymob HMAC verification failed")
        return data

    def retrieve_subscription(self, subscription_id: str) -> dict:
        """Paymob doesn't have subscription objects — return a stub."""
        return {"id": subscription_id, "status": "active"}

    def handle_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookResult:
        data = self.construct_webhook_event(payload, signature, secret)
        obj = data.get("obj", {})
        event_type = data.get("type", "TRANSACTION.PROCESSED")
        success: bool = bool(obj.get("success"))
        order: dict = obj.get("order", {}) or {}
        # merchant_order_id format: "paymob_<tenant_id>:<plan_key>"
        merchant_order_id: str = str(order.get("merchant_order_id", ""))
        plan: str | None = None
        tenant_id: int | None = None
        if ":" in merchant_order_id:
            prefix, plan = merchant_order_id.split(":", 1)
            raw_tid = prefix.removeprefix("paymob_")
            if raw_tid.isdigit():
                tenant_id = int(raw_tid)
        logger.info(
            "paymob_webhook",
            event_type=event_type,
            success=success,
            plan=plan,
            tenant_id=tenant_id,
        )
        return WebhookResult(
            event_type=event_type,
            plan=plan if success else None,
            tenant_id=tenant_id if success else None,
            status="completed" if success else "failed",
        )

    def cancel_subscription(self, external_subscription_id: str) -> None:
        """No-op — Paymob recurring is managed via the dashboard."""

    # ── POS payment (issue #738) ─────────────────────────────────────────────

    def create_pos_payment_session(
        self,
        amount: Decimal,
        merchant_ref: str,
        currency: str = "EGP",
    ) -> dict:
        """Initiate a POS card-payment session through Paymob.

        Unlike :meth:`create_checkout_session` (which is for subscription
        billing and looks up amount from plan limits), this method accepts
        ``amount`` directly in the currency unit (e.g. EGP, not piastres).

        ``merchant_ref`` is forwarded as ``merchant_order_id`` — Paymob
        deduplicates orders with the same ``merchant_order_id``, giving us
        idempotency protection against double-charges on retry (#738).

        Returns a dict with at least ``"order_id"`` so callers do not need
        to import internal Paymob shim types.
        """
        from decimal import Decimal as _Decimal  # local import avoids unused at module level

        amount_piastres = int(_Decimal(str(amount)) * 100)
        auth_token = self._auth_token()
        order_id = self._register_order(auth_token, amount_piastres, merchant_ref)
        logger.info(
            "paymob_pos_payment_initiated",
            order_id=order_id,
            merchant_ref=merchant_ref,
            currency=currency,
        )
        return {"order_id": order_id}

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _auth_token(self) -> str:
        resp = httpx.post(f"{_BASE}/auth/tokens", json={"api_key": self._api_key}, timeout=10)
        resp.raise_for_status()
        return str(resp.json()["token"])

    def _register_order(self, token: str, amount: int, merchant_order_id: str) -> str:
        payload = {
            "auth_token": token,
            "delivery_needed": False,
            "amount_cents": amount,
            "currency": "EGP",
            "merchant_order_id": merchant_order_id,
            "items": [],
        }
        resp = httpx.post(f"{_BASE}/ecommerce/orders", json=payload, timeout=10)
        resp.raise_for_status()
        return str(resp.json()["id"])

    def _payment_key(self, token: str, order_id: str, amount: int) -> str:
        payload = {
            "auth_token": token,
            "amount_cents": amount,
            "expiration": 3600,
            "order_id": order_id,
            "billing_data": {
                "apartment": "NA",
                "email": "NA",
                "floor": "NA",
                "first_name": "NA",
                "street": "NA",
                "building": "NA",
                "phone_number": "NA",
                "shipping_method": "NA",
                "postal_code": "NA",
                "city": "NA",
                "country": "EG",
                "last_name": "NA",
                "state": "NA",
            },
            "currency": "EGP",
            "integration_id": int(self._integration_id),
        }
        resp = httpx.post(f"{_BASE}/acceptance/payment_keys", json=payload, timeout=10)
        resp.raise_for_status()
        return str(resp.json()["token"])

    @staticmethod
    def _calc_hmac(obj: dict[str, Any], secret: str) -> str:
        """Compute Paymob HMAC-SHA512 over the sorted notification fields."""
        parts: list[str] = []
        for key in _HMAC_FIELDS:
            if "." in key:
                top, sub = key.split(".", 1)
                val = (obj.get(top) or {}).get(sub, "")
            else:
                val = obj.get(key, "")
            parts.append(str(val))
        message = "".join(parts)
        return hmac.new(secret.encode(), message.encode(), hashlib.sha512).hexdigest()
