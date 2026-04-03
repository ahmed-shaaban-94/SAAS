"""Billing service — orchestrates Stripe operations and plan management."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from datapulse.billing.models import BillingStatus, CheckoutResponse, PortalResponse, WebhookResult
from datapulse.billing.plans import DEFAULT_PLAN, get_plan_limits, resolve_plan_from_price
from datapulse.billing.repository import BillingRepository
from datapulse.billing.stripe_client import StripeClient

logger = structlog.get_logger()


class BillingService:
    """Coordinates billing operations between Stripe, DB, and plan enforcement."""

    def __init__(
        self,
        repo: BillingRepository,
        stripe_client: StripeClient,
        *,
        price_to_plan: dict[str, str],
        base_url: str = "https://smartdatapulse.tech",
    ) -> None:
        self._repo = repo
        self._stripe = stripe_client
        self._price_to_plan = price_to_plan
        self._base_url = base_url

    def get_billing_status(self, tenant_id: int) -> BillingStatus:
        plan_name = self._repo.get_tenant_plan(tenant_id)
        limits = get_plan_limits(plan_name)
        usage = self._repo.get_usage(tenant_id)
        sub = self._repo.get_active_subscription(tenant_id)

        return BillingStatus(
            plan=plan_name,
            plan_name=limits.name,
            price_display=limits.price_display,
            subscription_status=sub["status"] if sub else None,
            current_period_end=sub["current_period_end"] if sub else None,
            cancel_at_period_end=sub["cancel_at_period_end"] if sub else False,
            data_sources_used=usage["data_sources_count"],
            data_sources_limit=limits.data_sources,
            total_rows_used=usage["total_rows"],
            total_rows_limit=limits.max_rows,
            ai_insights=limits.ai_insights,
            pipeline_automation=limits.pipeline_automation,
            quality_gates=limits.quality_gates,
        )

    def create_checkout_session(
        self,
        *,
        tenant_id: int,
        tenant_name: str,
        email: str,
        price_id: str,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> CheckoutResponse:
        if not self._stripe.is_configured:
            msg = "Stripe is not configured"
            raise RuntimeError(msg)

        # Get or create Stripe customer
        customer_id = self._repo.get_stripe_customer_id(tenant_id)
        if not customer_id:
            customer = self._stripe.create_customer(
                email=email,
                name=tenant_name,
                metadata={"tenant_id": str(tenant_id)},
            )
            customer_id = customer.id
            self._repo.set_stripe_customer_id(tenant_id, customer_id)
            logger.info("stripe_customer_created", tenant_id=tenant_id, customer_id=customer_id)

        session = self._stripe.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success_url or f"{self._base_url}/billing?success=true",
            cancel_url=cancel_url or f"{self._base_url}/billing?canceled=true",
        )

        return CheckoutResponse(checkout_url=session.url)

    def create_portal_session(self, tenant_id: int) -> PortalResponse:
        if not self._stripe.is_configured:
            msg = "Stripe is not configured"
            raise RuntimeError(msg)

        customer_id = self._repo.get_stripe_customer_id(tenant_id)
        if not customer_id:
            msg = "No Stripe customer found for this tenant"
            raise ValueError(msg)

        session = self._stripe.create_portal_session(
            customer_id=customer_id,
            return_url=f"{self._base_url}/billing",
        )

        return PortalResponse(portal_url=session.url)

    def handle_webhook_event(
        self, payload: bytes, sig_header: str, webhook_secret: str
    ) -> WebhookResult:
        event = self._stripe.construct_webhook_event(payload, sig_header, webhook_secret)
        event_type = event["type"]
        data_object = event["data"]["object"]

        logger.info("stripe_webhook_received", event_type=event_type)

        if event_type == "checkout.session.completed":
            return self._handle_checkout_completed(data_object)
        elif event_type == "customer.subscription.updated":
            return self._handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(data_object)
        elif event_type == "invoice.payment_failed":
            return self._handle_payment_failed(data_object)
        else:
            logger.debug("stripe_webhook_ignored", event_type=event_type)
            return WebhookResult(event_type=event_type, status="ignored")

    # ── Private webhook handlers ────────────────────────────────

    def _handle_checkout_completed(self, session: dict) -> WebhookResult:
        customer_id = session["customer"]
        subscription_id = session.get("subscription")
        if not subscription_id:
            return WebhookResult(event_type="checkout.session.completed", status="no_subscription")

        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        if not tenant_id:
            logger.warning("webhook_unknown_customer", customer_id=customer_id)
            return WebhookResult(event_type="checkout.session.completed", status="unknown_customer")

        sub = self._stripe.retrieve_subscription(subscription_id)
        price_id = sub["items"]["data"][0]["price"]["id"]
        plan = resolve_plan_from_price(price_id, self._price_to_plan)

        self._repo.upsert_subscription(
            tenant_id=tenant_id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id,
            status=sub["status"],
            current_period_start=_ts_to_dt(sub["current_period_start"]),
            current_period_end=_ts_to_dt(sub["current_period_end"]),
            cancel_at_period_end=sub.get("cancel_at_period_end", False),
        )
        self._repo.update_tenant_plan(tenant_id, plan)

        logger.info("checkout_completed", tenant_id=tenant_id, plan=plan)
        return WebhookResult(
            event_type="checkout.session.completed", tenant_id=tenant_id, plan=plan
        )

    def _handle_subscription_updated(self, sub: dict) -> WebhookResult:
        customer_id = sub["customer"]
        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        if not tenant_id:
            return WebhookResult(event_type="customer.subscription.updated", status="unknown_customer")

        price_id = sub["items"]["data"][0]["price"]["id"]
        plan = resolve_plan_from_price(price_id, self._price_to_plan)

        self._repo.upsert_subscription(
            tenant_id=tenant_id,
            stripe_subscription_id=sub["id"],
            stripe_price_id=price_id,
            status=sub["status"],
            current_period_start=_ts_to_dt(sub["current_period_start"]),
            current_period_end=_ts_to_dt(sub["current_period_end"]),
            cancel_at_period_end=sub.get("cancel_at_period_end", False),
        )
        self._repo.update_tenant_plan(tenant_id, plan)

        logger.info("subscription_updated", tenant_id=tenant_id, plan=plan, status=sub["status"])
        return WebhookResult(
            event_type="customer.subscription.updated", tenant_id=tenant_id, plan=plan
        )

    def _handle_subscription_deleted(self, sub: dict) -> WebhookResult:
        customer_id = sub["customer"]
        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        if not tenant_id:
            return WebhookResult(event_type="customer.subscription.deleted", status="unknown_customer")

        self._repo.upsert_subscription(
            tenant_id=tenant_id,
            stripe_subscription_id=sub["id"],
            stripe_price_id=sub["items"]["data"][0]["price"]["id"],
            status="canceled",
        )
        self._repo.update_tenant_plan(tenant_id, DEFAULT_PLAN)

        logger.info("subscription_canceled", tenant_id=tenant_id)
        return WebhookResult(
            event_type="customer.subscription.deleted",
            tenant_id=tenant_id,
            plan=DEFAULT_PLAN,
        )

    def _handle_payment_failed(self, invoice: dict) -> WebhookResult:
        customer_id = invoice["customer"]
        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        sub_id = invoice.get("subscription")

        if tenant_id and sub_id:
            self._repo.upsert_subscription(
                tenant_id=tenant_id,
                stripe_subscription_id=sub_id,
                stripe_price_id=invoice.get("lines", {}).get("data", [{}])[0].get("price", {}).get("id", ""),
                status="past_due",
            )
            logger.warning("payment_failed", tenant_id=tenant_id, subscription_id=sub_id)

        return WebhookResult(
            event_type="invoice.payment_failed",
            tenant_id=tenant_id,
            status="past_due",
        )


def _ts_to_dt(ts: int | None) -> datetime | None:
    """Convert a Unix timestamp to a timezone-aware datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)
