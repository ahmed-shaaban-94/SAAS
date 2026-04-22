"""Billing service — orchestrates Stripe operations and plan management."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog

from datapulse.billing.models import (
    BillingStatus,
    CheckoutResponse,
    PortalResponse,
    WebhookResult,
)
from datapulse.billing.plans import (
    DEFAULT_PLAN,
    get_plan_limits,
    resolve_plan_from_price,
)
from datapulse.billing.provider import PaymentProvider, ProviderUnavailableError
from datapulse.billing.repository import BillingRepository

logger = structlog.get_logger()

_CHECKOUT_COMPLETED = "checkout.session.completed"
_SUB_UPDATED = "customer.subscription.updated"
_SUB_DELETED = "customer.subscription.deleted"
_PAYMENT_FAILED = "invoice.payment_failed"


class PlanLimitExceededError(Exception):
    """Raised when a tenant operation would exceed their plan limits."""

    def __init__(self, limit_type: str, current: int, limit: int, plan: str) -> None:
        self.limit_type = limit_type
        self.current = current
        self.limit = limit
        self.plan = plan
        super().__init__(
            f"{limit_type} limit exceeded: {current}/{limit} on {plan} plan. "
            f"Upgrade to increase your limit."
        )


class BillingService:
    """Business logic for subscriptions, plans, usage, and provider routing."""

    def __init__(
        self,
        repo: BillingRepository,
        providers: dict[str, PaymentProvider],
        *,
        price_to_plan: dict[str, str],
        base_url: str = "https://smartdatapulse.tech",
    ) -> None:
        self._repo = repo
        self._providers = providers
        # Back-compat shim — checkout/portal/webhook code paths still reference
        # self._stripe directly. Route all new access through _provider_for;
        # existing call-sites migrate in a follow-up task (PR 2 keeps behaviour).
        self._stripe = providers.get("USD")  # type: ignore[assignment]
        self._price_to_plan = price_to_plan
        self._base_url = base_url

    def _provider_for(self, currency: str) -> PaymentProvider:
        """Return the PaymentProvider registered for *currency* (ISO-4217 uppercase).

        Raises ProviderUnavailableError when no provider is configured for the
        requested currency — surfaces as HTTP 503 in billing routes.
        """
        provider = self._providers.get(currency.upper())
        if provider is None:
            raise ProviderUnavailableError(currency)
        return provider

    def check_plan_limits(
        self,
        tenant_id: int,
        *,
        additional_rows: int = 0,
        additional_sources: int = 0,
    ) -> None:
        """Validate that the tenant has not exceeded their plan limits.

        Raises PlanLimitExceededError if:
        - Current usage already meets or exceeds the limit, OR
        - Adding the requested resources would exceed the limit.
        A limit of -1 means unlimited.
        """
        plan_name = self._repo.get_tenant_plan(tenant_id)
        limits = get_plan_limits(plan_name)
        usage = self._repo.get_usage(tenant_id)

        # Check data sources limit (current + projected)
        if limits.data_sources != -1:
            current_sources = usage["data_sources_count"]
            if current_sources >= limits.data_sources:
                raise PlanLimitExceededError(
                    limit_type="data_sources",
                    current=current_sources,
                    limit=limits.data_sources,
                    plan=plan_name,
                )
            projected = current_sources + additional_sources
            if additional_sources > 0 and projected > limits.data_sources:
                raise PlanLimitExceededError(
                    limit_type="data_sources",
                    current=current_sources,
                    limit=limits.data_sources,
                    plan=plan_name,
                )

        # Check row limit (current + projected)
        if limits.max_rows != -1:
            current_rows = usage["total_rows"]
            if current_rows >= limits.max_rows:
                raise PlanLimitExceededError(
                    limit_type="total_rows",
                    current=current_rows,
                    limit=limits.max_rows,
                    plan=plan_name,
                )
            if additional_rows > 0 and current_rows + additional_rows > limits.max_rows:
                raise PlanLimitExceededError(
                    limit_type="total_rows",
                    current=current_rows,
                    limit=limits.max_rows,
                    plan=plan_name,
                )

        logger.info(
            "plan_limits_checked",
            tenant_id=tenant_id,
            plan=plan_name,
        )

    _FEATURE_FLAGS: frozenset[str] = frozenset(
        {
            "ai_insights",
            "pipeline_automation",
            "quality_gates",
        }
    )

    def check_feature_access(self, tenant_id: int, feature: str) -> bool:
        """Check if a tenant's plan includes a specific feature.

        Only boolean feature flags defined in PlanLimits are allowed.
        Raises ValueError for unknown feature names.
        """
        if feature not in self._FEATURE_FLAGS:
            raise ValueError(f"Unknown feature flag: {feature!r}")
        plan_name = self._repo.get_tenant_plan(tenant_id)
        limits = get_plan_limits(plan_name)
        return bool(getattr(limits, feature))

    def update_usage(
        self,
        tenant_id: int,
        *,
        data_sources_count: int | None = None,
        total_rows: int | None = None,
    ) -> None:
        """Update usage metrics for a tenant after a pipeline run or data source change."""
        self._repo.upsert_usage(
            tenant_id,
            data_sources_count=data_sources_count,
            total_rows=total_rows,
        )
        logger.info(
            "usage_updated",
            tenant_id=tenant_id,
            data_sources_count=data_sources_count,
            total_rows=total_rows,
        )

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
            cancel_at_period_end=(sub["cancel_at_period_end"] if sub else False),
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

        _validate_callback_url(success_url, self._base_url)
        _validate_callback_url(cancel_url, self._base_url)

        customer_id = self._repo.get_stripe_customer_id(tenant_id)
        if not customer_id:
            customer = self._stripe.create_customer(
                email=email,
                name=tenant_name,
                metadata={"tenant_id": str(tenant_id)},
            )
            customer_id = customer.id
            self._repo.set_stripe_customer_id(tenant_id, customer_id)
            logger.info(
                "stripe_customer_created",
                tenant_id=tenant_id,
                customer_id=customer_id,
            )

        success = success_url or f"{self._base_url}/billing?success=true"
        cancel = cancel_url or f"{self._base_url}/billing?canceled=true"

        session = self._stripe.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success,
            cancel_url=cancel,
        )

        url: str = session.url or ""
        return CheckoutResponse(checkout_url=url)

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

        handlers = {
            _CHECKOUT_COMPLETED: self._handle_checkout_completed,
            _SUB_UPDATED: self._handle_subscription_updated,
            _SUB_DELETED: self._handle_subscription_deleted,
            _PAYMENT_FAILED: self._handle_payment_failed,
        }
        handler = handlers.get(event_type)
        if handler:
            return handler(data_object)

        logger.debug("stripe_webhook_ignored", event_type=event_type)
        return WebhookResult(event_type=event_type, status="ignored")

    # ── Private webhook handlers ──────────────────────────────

    def _handle_checkout_completed(self, session: dict) -> WebhookResult:
        customer_id = session["customer"]
        subscription_id = session.get("subscription")
        if not subscription_id:
            return WebhookResult(event_type=_CHECKOUT_COMPLETED, status="no_subscription")

        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        if not tenant_id:
            logger.warning("webhook_unknown_customer", customer_id=customer_id)
            return WebhookResult(event_type=_CHECKOUT_COMPLETED, status="unknown_customer")

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
            cancel_at_period_end=bool(sub["cancel_at_period_end"]),
        )
        self._repo.update_tenant_plan(tenant_id, plan)

        logger.info("checkout_completed", tenant_id=tenant_id, plan=plan)
        return WebhookResult(
            event_type=_CHECKOUT_COMPLETED,
            tenant_id=tenant_id,
            plan=plan,
        )

    def _handle_subscription_updated(self, sub: dict) -> WebhookResult:
        customer_id = sub["customer"]
        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        if not tenant_id:
            return WebhookResult(event_type=_SUB_UPDATED, status="unknown_customer")

        price_id = sub["items"]["data"][0]["price"]["id"]
        plan = resolve_plan_from_price(price_id, self._price_to_plan)

        self._repo.upsert_subscription(
            tenant_id=tenant_id,
            stripe_subscription_id=sub["id"],
            stripe_price_id=price_id,
            status=sub["status"],
            current_period_start=_ts_to_dt(sub["current_period_start"]),
            current_period_end=_ts_to_dt(sub["current_period_end"]),
            cancel_at_period_end=bool(sub.get("cancel_at_period_end", False)),
        )
        self._repo.update_tenant_plan(tenant_id, plan)

        logger.info(
            "subscription_updated",
            tenant_id=tenant_id,
            plan=plan,
            status=sub["status"],
        )
        return WebhookResult(event_type=_SUB_UPDATED, tenant_id=tenant_id, plan=plan)

    def _handle_subscription_deleted(self, sub: dict) -> WebhookResult:
        customer_id = sub["customer"]
        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        if not tenant_id:
            return WebhookResult(event_type=_SUB_DELETED, status="unknown_customer")

        price_id = sub["items"]["data"][0]["price"]["id"]
        self._repo.upsert_subscription(
            tenant_id=tenant_id,
            stripe_subscription_id=sub["id"],
            stripe_price_id=price_id,
            status="canceled",
        )
        self._repo.update_tenant_plan(tenant_id, DEFAULT_PLAN)

        logger.info("subscription_canceled", tenant_id=tenant_id)
        return WebhookResult(
            event_type=_SUB_DELETED,
            tenant_id=tenant_id,
            plan=DEFAULT_PLAN,
        )

    def _handle_payment_failed(self, invoice: dict) -> WebhookResult:
        customer_id = invoice["customer"]
        tenant_id = self._repo.get_tenant_by_stripe_customer(customer_id)
        sub_id = invoice.get("subscription")

        if tenant_id and sub_id:
            lines = invoice.get("lines", {})
            line_data = lines.get("data", [{}])
            price_obj = line_data[0].get("price", {})
            price_id = price_obj.get("id", "")
            self._repo.upsert_subscription(
                tenant_id=tenant_id,
                stripe_subscription_id=sub_id,
                stripe_price_id=price_id,
                status="past_due",
            )
            logger.warning(
                "payment_failed",
                tenant_id=tenant_id,
                subscription_id=sub_id,
            )

        return WebhookResult(
            event_type=_PAYMENT_FAILED,
            tenant_id=tenant_id,
            status="past_due",
        )


def _validate_callback_url(url: str | None, base_url: str) -> None:
    """Raise ValueError if url is set but its netloc differs from base_url.

    Prevents open redirects to phishing domains passed as success_url/cancel_url.
    """
    if url is None:
        return
    parsed = urlparse(url)
    allowed_netloc = urlparse(base_url).netloc
    if parsed.netloc != allowed_netloc:
        raise ValueError(
            f"Callback URL domain '{parsed.netloc}' is not allowed; must be '{allowed_netloc}'"
        )


def _ts_to_dt(ts: int | None) -> datetime | None:
    """Convert a Unix timestamp to a timezone-aware datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)
