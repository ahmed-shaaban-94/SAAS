"""Tests for BillingService.handle_webhook_event() — H5.2.

Covers the four Stripe event types that the service handles:
  - checkout.session.completed  → upsert subscription + set plan
  - customer.subscription.deleted → cancel subscription, downgrade to starter
  - invoice.payment_failed      → mark subscription as past_due
  - unknown event type          → ignored (no DB writes)

All tests mock the Stripe client (construct_webhook_event) and the
BillingRepository so no real network calls or DB connections are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest

from datapulse.billing.models import WebhookResult
from datapulse.billing.repository import BillingRepository
from datapulse.billing.service import BillingService
from datapulse.billing.stripe_client import StripeClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRICE_TO_PLAN = {"price_pro_monthly": "pro", "price_starter_monthly": "starter"}
_BASE_URL = "https://example.datapulse.tech"

_TS_START = 1_700_000_000  # 2023-11-14 22:13:20 UTC
_TS_END = 1_702_592_000  # 2023-12-14 22:13:20 UTC


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(BillingRepository, instance=True)


@pytest.fixture()
def mock_stripe() -> MagicMock:
    client = create_autospec(StripeClient, instance=True)
    client.is_configured = True
    return client


@pytest.fixture()
def billing_service(mock_repo: MagicMock, mock_stripe: MagicMock) -> BillingService:
    return BillingService(
        repo=mock_repo,
        providers={"USD": mock_stripe},
        price_to_plan=_PRICE_TO_PLAN,
        base_url=_BASE_URL,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fire_webhook(
    service: BillingService,
    mock_stripe: MagicMock,
    event_type: str,
    data_object: dict,
) -> WebhookResult:
    """Wire construct_webhook_event to return a synthetic event and call handle_webhook_event."""
    mock_stripe.construct_webhook_event.return_value = {
        "type": event_type,
        "data": {"object": data_object},
    }
    return service.handle_webhook_event(b"payload", "sig_header=v1,t=1", "whsec_test")


def _sub_object(
    *,
    status: str = "active",
    sub_id: str = "sub_abc",
    customer: str = "cus_123",
    price_id: str = "price_pro_monthly",
    cancel_at_period_end: bool = False,
) -> dict:
    """Build a minimal Stripe subscription object dict."""
    return {
        "id": sub_id,
        "customer": customer,
        "status": status,
        "items": {"data": [{"price": {"id": price_id}}]},
        "current_period_start": _TS_START,
        "current_period_end": _TS_END,
        "cancel_at_period_end": cancel_at_period_end,
    }


# ---------------------------------------------------------------------------
# H5.2.1 — checkout.session.completed
# ---------------------------------------------------------------------------


class TestCheckoutCompleted:
    def test_known_customer_upserts_subscription_and_sets_plan(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """checkout.session.completed with a known customer must upsert the subscription
        and update the tenant's plan."""
        mock_repo.get_tenant_by_stripe_customer.return_value = 42
        mock_stripe.retrieve_subscription.return_value = _sub_object()

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_abc"},
        )

        assert result.event_type == "checkout.session.completed"
        assert result.status == "processed"
        assert result.tenant_id == 42
        assert result.plan == "pro"

        mock_repo.upsert_subscription.assert_called_once()
        mock_repo.update_tenant_plan.assert_called_once_with(42, "pro")

    def test_unknown_customer_returns_unknown_status(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """checkout.session.completed for an unknown customer must return 'unknown_customer'."""
        mock_repo.get_tenant_by_stripe_customer.return_value = None

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "checkout.session.completed",
            {"customer": "cus_unknown", "subscription": "sub_xyz"},
        )

        assert result.status == "unknown_customer"
        mock_repo.upsert_subscription.assert_not_called()
        mock_repo.update_tenant_plan.assert_not_called()

    def test_no_subscription_returns_no_subscription_status(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """checkout.session.completed without a subscription ID returns 'no_subscription'."""
        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "checkout.session.completed",
            {"customer": "cus_123", "subscription": None},
        )

        assert result.status == "no_subscription"
        mock_repo.upsert_subscription.assert_not_called()


# ---------------------------------------------------------------------------
# H5.2.2 — customer.subscription.deleted
# ---------------------------------------------------------------------------


class TestSubscriptionDeleted:
    def test_known_customer_cancels_and_downgrades(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """subscription.deleted must cancel the DB record and downgrade the plan to starter."""
        mock_repo.get_tenant_by_stripe_customer.return_value = 7

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "customer.subscription.deleted",
            _sub_object(status="canceled", customer="cus_007"),
        )

        assert result.event_type == "customer.subscription.deleted"
        assert result.tenant_id == 7
        assert result.plan == "starter"

        # upsert_subscription must record status="canceled"
        call_kwargs = mock_repo.upsert_subscription.call_args.kwargs
        assert call_kwargs["status"] == "canceled"
        mock_repo.update_tenant_plan.assert_called_once_with(7, "starter")

    def test_unknown_customer_returns_unknown_status(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """subscription.deleted for unknown customer returns 'unknown_customer'."""
        mock_repo.get_tenant_by_stripe_customer.return_value = None

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "customer.subscription.deleted",
            _sub_object(customer="cus_ghost"),
        )

        assert result.status == "unknown_customer"
        mock_repo.update_tenant_plan.assert_not_called()


# ---------------------------------------------------------------------------
# H5.2.3 — invoice.payment_failed
# ---------------------------------------------------------------------------


class TestPaymentFailed:
    def test_known_customer_marks_past_due(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """invoice.payment_failed must mark the subscription as past_due."""
        mock_repo.get_tenant_by_stripe_customer.return_value = 5

        invoice_obj = {
            "customer": "cus_late",
            "subscription": "sub_late",
            "lines": {"data": [{"price": {"id": "price_pro_monthly"}}]},
        }

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "invoice.payment_failed",
            invoice_obj,
        )

        assert result.event_type == "invoice.payment_failed"
        assert result.status == "past_due"
        assert result.tenant_id == 5

        call_kwargs = mock_repo.upsert_subscription.call_args.kwargs
        assert call_kwargs["status"] == "past_due"

    def test_unknown_customer_still_returns_result(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """invoice.payment_failed for unknown customer returns result without DB upsert."""
        mock_repo.get_tenant_by_stripe_customer.return_value = None

        invoice_obj = {
            "customer": "cus_anon",
            "subscription": "sub_anon",
            "lines": {"data": []},
        }

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "invoice.payment_failed",
            invoice_obj,
        )

        assert result.event_type == "invoice.payment_failed"
        assert result.status == "past_due"
        # No subscription to update when tenant is unknown
        mock_repo.upsert_subscription.assert_not_called()


# ---------------------------------------------------------------------------
# H5.2.4 — Unknown event type
# ---------------------------------------------------------------------------


class TestUnknownEvent:
    def test_unknown_event_type_ignored(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """Unrecognised Stripe event types must return 'ignored' and make no DB writes."""
        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "charge.refunded",  # not in the handler map
            {"id": "ch_xxx"},
        )

        assert result.event_type == "charge.refunded"
        assert result.status == "ignored"
        mock_repo.upsert_subscription.assert_not_called()
        mock_repo.update_tenant_plan.assert_not_called()

    def test_subscription_updated_resolves_plan(
        self, billing_service: BillingService, mock_repo: MagicMock, mock_stripe: MagicMock
    ) -> None:
        """customer.subscription.updated must resolve the plan from the price mapping."""
        mock_repo.get_tenant_by_stripe_customer.return_value = 12

        result = _fire_webhook(
            billing_service,
            mock_stripe,
            "customer.subscription.updated",
            _sub_object(customer="cus_12", price_id="price_pro_monthly"),
        )

        assert result.plan == "pro"
        assert result.tenant_id == 12
        mock_repo.update_tenant_plan.assert_called_once_with(12, "pro")
