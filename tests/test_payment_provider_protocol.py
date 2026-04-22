# tests/test_payment_provider_protocol.py
"""Protocol conformance tests for PaymentProvider (#604 Spec 1 PR 2)."""

from datapulse.billing.provider import PaymentProvider, ProviderUnavailableError
from datapulse.billing.stripe_client import StripeClient


class TestPaymentProviderProtocol:
    def test_stripe_client_satisfies_protocol(self):
        client = StripeClient(secret_key="sk_test_dummy")
        assert isinstance(client, PaymentProvider)

    def test_stripe_client_declares_usd_currency(self):
        client = StripeClient(secret_key="sk_test_dummy")
        assert client.name == "stripe"
        assert client.currencies == frozenset({"USD"})

    def test_provider_unavailable_error_carries_currency(self):
        err = ProviderUnavailableError("EGP")
        assert err.currency == "EGP"
        assert "EGP" in str(err)
