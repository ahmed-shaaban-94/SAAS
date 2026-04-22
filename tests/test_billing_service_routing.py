# tests/test_billing_service_routing.py
"""Currency-based routing inside BillingService (#604 Spec 1 PR 2)."""

from unittest.mock import MagicMock, create_autospec

import pytest

from datapulse.billing.provider import PaymentProvider, ProviderUnavailableError
from datapulse.billing.repository import BillingRepository
from datapulse.billing.service import BillingService


def _stub_provider(currency: str, name: str) -> MagicMock:
    p = MagicMock(spec=PaymentProvider)
    p.name = name
    p.currencies = frozenset({currency})
    return p


def _billing_service(providers: dict) -> BillingService:
    repo = create_autospec(BillingRepository, instance=True)
    return BillingService(
        repo=repo,
        providers=providers,
        price_to_plan={},
        base_url="https://example.test",
    )


class TestBillingServiceRouting:
    def test_usd_tenant_routes_to_stripe_provider(self):
        stripe = _stub_provider("USD", "stripe")
        svc = _billing_service({"USD": stripe})
        assert svc._provider_for("USD") is stripe

    def test_egp_tenant_raises_provider_unavailable(self):
        stripe = _stub_provider("USD", "stripe")
        svc = _billing_service({"USD": stripe})
        with pytest.raises(ProviderUnavailableError) as exc_info:
            svc._provider_for("EGP")
        assert exc_info.value.currency == "EGP"

    def test_unknown_currency_raises(self):
        svc = _billing_service({})
        with pytest.raises(ProviderUnavailableError):
            svc._provider_for("JPY")
