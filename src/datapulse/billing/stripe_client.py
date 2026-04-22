"""Thin Stripe SDK wrapper for testability."""

from __future__ import annotations

import stripe
import structlog

from datapulse.billing.models import WebhookResult

logger = structlog.get_logger()


class StripeClient:
    """Wraps stripe SDK calls so they can be mocked in tests."""

    name = "stripe"
    currencies = frozenset({"USD"})

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key
        stripe.api_key = secret_key

    @property
    def is_configured(self) -> bool:
        return bool(self._secret_key)

    def create_customer(self, *, email: str, name: str, metadata: dict) -> stripe.Customer:
        return stripe.Customer.create(email=email, name=name, metadata=metadata)

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> stripe.checkout.Session:
        return stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )

    def create_portal_session(
        self, *, customer_id: str, return_url: str
    ) -> stripe.billing_portal.Session:
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

    def construct_webhook_event(
        self, payload: bytes, sig_header: str, webhook_secret: str
    ) -> stripe.Event:
        return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

    def retrieve_subscription(self, subscription_id: str) -> stripe.Subscription:
        return stripe.Subscription.retrieve(subscription_id)

    def handle_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookResult:
        """Process a raw Stripe webhook payload and return a structured result."""
        event = self.construct_webhook_event(payload, signature, secret)
        return WebhookResult(event_type=event["type"])

    def cancel_subscription(self, external_subscription_id: str) -> None:
        """Cancel a Stripe subscription at period end."""
        stripe.Subscription.modify(external_subscription_id, cancel_at_period_end=True)
