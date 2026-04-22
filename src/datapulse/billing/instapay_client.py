"""InstaPay bank-transfer provider — manual reconciliation flow (issue #604).

InstaPay is Egypt's real-time bank transfer network. There is no programmatic
API for accepting payments; the flow is:

  1. Tenant initiates checkout → receives bank account details + reference.
  2. Tenant transfers the EGP amount to the DataPulse bank account.
  3. Tenant uploads proof of payment via POST /billing/instapay/upload-proof.
  4. Admin reviews and approves via POST /billing/instapay/approve.
  5. On approval, the subscription is activated (same DB path as Stripe webhooks).

This client satisfies the PaymentProvider Protocol — the create_checkout_session
method returns a static instructions URL rather than a payment gateway redirect.
Webhook handling and subscription management are effectively no-ops because the
event pipeline is driven by the admin approval endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from datapulse.billing.models import WebhookResult

logger = structlog.get_logger()

# Published in the dashboard / onboarding emails. No secrets here — this is
# the same info printed on paper invoices.
_INSTAPAY_INSTRUCTIONS_PATH = "/billing/instapay/instructions"


@dataclass
class _InstapaySession:
    """Checkout-session shim with a `.url` attribute (mirrors Stripe)."""

    url: str
    reference: str = ""


class InstaPayClient:
    """PaymentProvider implementation for InstaPay bank transfers (EGP)."""

    name = "instapay"
    currencies: frozenset[str] = frozenset({"EGP"})

    def __init__(self, base_url: str = "https://smartdatapulse.tech") -> None:
        self._base_url = base_url

    @property
    def is_configured(self) -> bool:
        return True  # No external credentials required

    # ── PaymentProvider Protocol ─────────────────────────────────────────────

    def create_customer(self, *, email: str, name: str, metadata: dict) -> dict:
        return {"email": email, "name": name, "id": f"instapay_{metadata.get('tenant_id', 'x')}"}

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> _InstapaySession:
        """Return instructions page URL; the tenant completes the bank transfer offline."""
        from datapulse.billing.plans import get_plan_limits

        limits = get_plan_limits(price_id)
        amount_egp = limits.price_egp // 100  # convert piastres → EGP

        reference = f"DP-{customer_id}-{price_id}".upper()
        instructions_url = (
            f"{self._base_url}{_INSTAPAY_INSTRUCTIONS_PATH}"
            f"?plan={price_id}&amount={amount_egp}&ref={reference}"
        )
        logger.info("instapay_checkout_initiated", reference=reference, plan=price_id)
        return _InstapaySession(url=instructions_url, reference=reference)

    def create_portal_session(self, *, customer_id: str, return_url: str) -> _InstapaySession:
        return _InstapaySession(url=return_url)

    def construct_webhook_event(self, payload: bytes, sig_header: str, webhook_secret: str) -> dict:
        """InstaPay has no push webhooks — approval is admin-driven."""
        raise NotImplementedError("InstaPay uses admin approval, not webhooks")

    def retrieve_subscription(self, subscription_id: str) -> dict:
        return {"id": subscription_id, "status": "active"}

    def handle_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookResult:
        """Not used — InstaPay subscriptions are activated via admin approval."""
        return WebhookResult(event_type="instapay.noop", status="skipped")

    def cancel_subscription(self, external_subscription_id: str) -> None:
        """No external API call needed — subscription is cancelled in the DB."""
