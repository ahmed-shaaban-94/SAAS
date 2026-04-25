"""Unit tests for POS payment gateways — B4.

Covers:
- CashGateway: exact, overpay (change), underpay (error)
- CardGateway stub: returns not-configured
- InsuranceGateway stub: requires insurance_no
- SplitPaymentProcessor: partial cash + partial insurance
- get_gateway: correct gateway returned for each method string
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from datapulse.pos.payment import (
    CardGateway,
    CashGateway,
    InsuranceGateway,
    PaymentResult,
    SplitPaymentProcessor,
    get_gateway,
)

# ---------------------------------------------------------------------------
# CashGateway
# ---------------------------------------------------------------------------


class TestCashGateway:
    def test_exact_payment(self):
        gw = CashGateway()
        result = gw.process_payment(Decimal("100"), tendered=Decimal("100"))
        assert result.success is True
        assert result.amount_charged == Decimal("100")
        assert result.change_due == Decimal("0")
        assert result.method == "cash"

    def test_overpayment_returns_change(self):
        gw = CashGateway()
        result = gw.process_payment(Decimal("135.50"), tendered=Decimal("200"))
        assert result.success is True
        assert result.change_due == Decimal("64.5000")

    def test_underpayment_returns_failure(self):
        gw = CashGateway()
        result = gw.process_payment(Decimal("100"), tendered=Decimal("50"))
        assert result.success is False
        assert result.amount_charged == Decimal("0")
        assert "Insufficient" in result.message

    def test_no_tendered_assumes_exact(self):
        """When tendered is None, cash gateway assumes exact amount."""
        gw = CashGateway()
        result = gw.process_payment(Decimal("75"))
        assert result.success is True
        assert result.change_due == Decimal("0")

    def test_large_change_precision(self):
        gw = CashGateway()
        result = gw.process_payment(Decimal("99.9999"), tendered=Decimal("100"))
        assert result.success is True
        assert result.change_due == Decimal("0.0001")

    def test_raise_if_failed_propagates_message(self):
        from datapulse.pos.exceptions import PosError

        result = PaymentResult(
            success=False, method="cash", amount_charged=Decimal("0"), message="fail"
        )
        with pytest.raises(PosError, match="fail"):
            result.raise_if_failed()

    def test_raise_if_failed_does_nothing_on_success(self):
        result = PaymentResult(success=True, method="cash", amount_charged=Decimal("10"))
        result.raise_if_failed()  # should not raise


# ---------------------------------------------------------------------------
# CardGateway (stub)
# ---------------------------------------------------------------------------


class TestCardGateway:
    def test_returns_not_configured(self):
        gw = CardGateway()
        result = gw.process_payment(Decimal("50"))
        assert result.success is False
        assert result.method == "card"
        # CardGateway is now a documented fallback stub; message directs operator
        # to set PAYMOB_API_KEY for real card processing (#738).
        msg = result.message.lower()
        assert "paymob_api_key" in msg or "paymobcardgateway" in msg

    def test_zero_charged_on_failure(self):
        gw = CardGateway()
        result = gw.process_payment(Decimal("999"))
        assert result.amount_charged == Decimal("0")


# ---------------------------------------------------------------------------
# InsuranceGateway (stub)
# ---------------------------------------------------------------------------


class TestInsuranceGateway:
    """Insurance stub fails closed — no authorization path until real insurer API.

    The prior stub returned success for any non-empty insurance number, which
    was a cash-register fraud vector (cashier types any string → sale marked
    paid). For pilot, every insurance attempt fails and the cashier must
    collect cash/card or capture the claim out-of-band.
    """

    def test_returns_failure_for_none(self):
        gw = InsuranceGateway()
        result = gw.process_payment(Decimal("50"), insurance_no=None)
        assert result.success is False
        assert result.amount_charged == Decimal("0")

    def test_returns_failure_for_empty(self):
        gw = InsuranceGateway()
        result = gw.process_payment(Decimal("50"), insurance_no="  ")
        assert result.success is False

    def test_returns_failure_even_for_valid_looking_number(self):
        gw = InsuranceGateway()
        result = gw.process_payment(Decimal("50"), insurance_no="INS-123456")
        assert result.success is False
        assert result.amount_charged == Decimal("0")
        assert "not yet configured" in result.message.lower()

    def test_no_authorization_code_emitted(self):
        """Prevents leaking the insurance number into the auth code field."""
        gw = InsuranceGateway()
        result = gw.process_payment(Decimal("50"), insurance_no="INS-123456")
        assert result.authorization_code is None

    def test_method_is_insurance(self):
        gw = InsuranceGateway()
        result = gw.process_payment(Decimal("30"), insurance_no="INS-999")
        assert result.method == "insurance"


# ---------------------------------------------------------------------------
# SplitPaymentProcessor
# ---------------------------------------------------------------------------


class TestSplitPaymentProcessor:
    def test_cash_plus_insurance_split_fails_closed(self):
        """Insurance leg fails closed until the real insurer API is wired —
        any split that includes insurance must fail overall, preventing the
        fraud path where a cashier splits a sale with a fake insurance leg.
        """
        proc = SplitPaymentProcessor()
        result = proc.process(
            grand_total=Decimal("135.50"),
            splits=[
                {"method": "cash", "amount": Decimal("100.00"), "tendered": Decimal("100.00")},
                {"method": "insurance", "amount": Decimal("35.50"), "insurance_no": "INS-123"},
            ],
        )
        assert result.success is False
        assert "insurance" in result.message.lower()

    def test_mismatched_totals_fail(self):
        proc = SplitPaymentProcessor()
        result = proc.process(
            grand_total=Decimal("100.00"),
            splits=[
                {"method": "cash", "amount": Decimal("40.00"), "tendered": Decimal("40.00")},
                # Only 40, but total is 100 → mismatch
            ],
        )
        assert result.success is False
        assert "do not equal" in result.message

    def test_failed_sub_payment_fails_split(self):
        proc = SplitPaymentProcessor()
        result = proc.process(
            grand_total=Decimal("100.00"),
            splits=[
                # underpay — cash split only covers 30 of required 50
                {"method": "cash", "amount": Decimal("50.00"), "tendered": Decimal("30.00")},
                {"method": "cash", "amount": Decimal("50.00"), "tendered": Decimal("50.00")},
            ],
        )
        assert result.success is False
        assert "cash" in result.message.lower()

    def test_change_totalled_across_splits(self):
        proc = SplitPaymentProcessor()
        result = proc.process(
            grand_total=Decimal("50.00"),
            splits=[
                {"method": "cash", "amount": Decimal("50.00"), "tendered": Decimal("60.00")},
            ],
        )
        assert result.success is True
        assert result.total_change == Decimal("10.0000")


# ---------------------------------------------------------------------------
# get_gateway factory
# ---------------------------------------------------------------------------


class TestGetGateway:
    def test_cash(self):
        gw = get_gateway("cash")
        assert isinstance(gw, CashGateway)

    def test_card(self):
        gw = get_gateway("card")
        assert isinstance(gw, CardGateway)

    def test_insurance(self):
        gw = get_gateway("insurance")
        assert isinstance(gw, InsuranceGateway)

    def test_unknown_defaults_to_cash(self):
        gw = get_gateway("bitcoin")
        assert isinstance(gw, CashGateway)
