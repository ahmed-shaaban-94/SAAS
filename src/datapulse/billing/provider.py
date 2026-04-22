"""Payment provider contract (#604 Spec 1).

Every billing integration (Stripe, Paymob, InstaPay) implements this Protocol.
``BillingService`` routes to the right provider based on tenant currency.

Sync (not async) to match existing StripeClient signatures — async buys
nothing since FastAPI handlers wrap these calls anyway. Protocol signatures
mirror the existing StripeClient (see ``src/datapulse/billing/stripe_client.py``)
so the current BillingService call-sites type-check without churn; future
providers (Paymob, InstaPay) implement the same shape.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from datapulse.billing.models import WebhookResult


class ProviderUnavailableError(Exception):
    """Raised when no payment provider is configured for a given currency.

    Surfaces as HTTP 503 in the billing routes so users see
    ``Payments in <currency> are temporarily unavailable`` instead of a 500.
    """

    def __init__(self, currency: str) -> None:
        self.currency = currency
        super().__init__(
            f"No payment provider configured for {currency!r}. "
            "Contact support — Egyptian billing (EGP) is coming soon."
        )


@runtime_checkable
class PaymentProvider(Protocol):
    """Shape every payment integration satisfies.

    Return types use ``Any`` for provider-specific objects (Stripe returns
    ``stripe.checkout.Session`` etc.) because other providers will return their
    own SDK types. ``WebhookResult`` is DataPulse-owned and stays typed.
    """

    name: str
    currencies: frozenset[str]

    @property
    def is_configured(self) -> bool: ...

    def create_customer(self, *, email: str, name: str, metadata: dict) -> Any: ...

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Any: ...

    def create_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
    ) -> Any: ...

    def construct_webhook_event(
        self, payload: bytes, sig_header: str, webhook_secret: str
    ) -> Any: ...

    def retrieve_subscription(self, subscription_id: str) -> Any: ...

    def handle_webhook_event(
        self, payload: bytes, signature: str, secret: str
    ) -> WebhookResult: ...

    def cancel_subscription(self, external_subscription_id: str) -> None: ...
