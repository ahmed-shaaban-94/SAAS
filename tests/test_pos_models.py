"""Tests for POS module Pydantic models.

Validates:
- All models can be constructed with valid data
- Frozen (immutable) enforcement — mutations raise TypeError
- Decimal precision is preserved (JsonDecimal)
- Field validation rejects invalid data
- Enum values accepted/rejected correctly
"""

from __future__ import annotations

import datetime
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datapulse.pos.constants import (
    CashDrawerEventType,
    PaymentMethod,
    ReceiptFormat,
    ReturnReason,
    TerminalStatus,
    TransactionStatus,
)
from datapulse.pos.models import (
    AddItemRequest,
    BatchSummary,
    CashCountRequest,
    CashDrawerEventResponse,
    CheckoutRequest,
    CheckoutResponse,
    EmailReceiptRequest,
    PharmacistVerifyRequest,
    PosCartItem,
    PosProductResult,
    PosStockInfo,
    ReturnRequest,
    ReturnResponse,
    ShiftSummaryResponse,
    TerminalCloseRequest,
    TerminalOpenRequest,
    TerminalSessionResponse,
    UpdateItemRequest,
    VoidRequest,
)

NOW = datetime.datetime(2026, 4, 15, 10, 0, 0, tzinfo=datetime.UTC)
TODAY = date(2026, 4, 15)


# ---------------------------------------------------------------------------
# PosCartItem
# ---------------------------------------------------------------------------


class TestPosCartItem:
    def test_basic_construction(self):
        item = PosCartItem(
            drug_code="DRUG001",
            drug_name="Panadol Extra 500mg",
            quantity=Decimal("2"),
            unit_price=Decimal("25.0000"),
            line_total=Decimal("50.0000"),
        )
        assert item.drug_code == "DRUG001"
        assert item.quantity == Decimal("2")
        assert item.line_total == Decimal("50.0000")
        assert item.discount == Decimal("0")
        assert item.is_controlled is False

    def test_with_batch_and_expiry(self):
        item = PosCartItem(
            drug_code="DRUG002",
            drug_name="Augmentin 1g",
            batch_number="BATCH-2026-042",
            expiry_date=date(2027, 3, 31),
            quantity=Decimal("1"),
            unit_price=Decimal("85.5000"),
            line_total=Decimal("85.5000"),
        )
        assert item.batch_number == "BATCH-2026-042"
        assert item.expiry_date == date(2027, 3, 31)

    def test_controlled_substance(self):
        item = PosCartItem(
            drug_code="DRUG999",
            drug_name="Tramadol 50mg",
            quantity=Decimal("1"),
            unit_price=Decimal("15.0000"),
            line_total=Decimal("15.0000"),
            is_controlled=True,
            pharmacist_id="PHARM-001",
        )
        assert item.is_controlled is True
        assert item.pharmacist_id == "PHARM-001"

    def test_frozen_immutable(self):
        item = PosCartItem(
            drug_code="DRUG001",
            drug_name="Panadol",
            quantity=Decimal("1"),
            unit_price=Decimal("10"),
            line_total=Decimal("10"),
        )
        with pytest.raises(ValidationError):
            item.quantity = Decimal("5")  # type: ignore[misc]

    def test_decimal_precision_preserved(self):
        item = PosCartItem(
            drug_code="D",
            drug_name="Drug",
            quantity=Decimal("1.5000"),
            unit_price=Decimal("99.9999"),
            line_total=Decimal("149.9999"),
        )
        # Decimal precision must NOT be rounded
        assert item.unit_price == Decimal("99.9999")
        assert item.line_total == Decimal("149.9999")


# ---------------------------------------------------------------------------
# TerminalOpenRequest / TerminalCloseRequest
# ---------------------------------------------------------------------------


class TestTerminalRequests:
    def test_open_defaults(self):
        req = TerminalOpenRequest(site_code="SITE01")
        assert req.terminal_name == "Terminal-1"
        assert req.opening_cash == Decimal("0")

    def test_open_custom(self):
        req = TerminalOpenRequest(
            site_code="SITE02",
            terminal_name="Cashier-3",
            opening_cash=Decimal("500.0000"),
        )
        assert req.terminal_name == "Cashier-3"
        assert req.opening_cash == Decimal("500.0000")

    def test_close_request(self):
        req = TerminalCloseRequest(closing_cash=Decimal("750.5000"))
        assert req.closing_cash == Decimal("750.5000")
        assert req.notes is None

    def test_open_frozen(self):
        req = TerminalOpenRequest(site_code="SITE01")
        with pytest.raises(ValidationError):
            req.site_code = "SITE99"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TerminalSessionResponse
# ---------------------------------------------------------------------------


class TestTerminalSessionResponse:
    def test_construction(self):
        resp = TerminalSessionResponse(
            id=1,
            site_code="SITE01",
            staff_id="STAFF-001",
            terminal_name="Terminal-1",
            status=TerminalStatus.active,
            opened_at=NOW,
            opening_cash=Decimal("200.0000"),
        )
        assert resp.status == TerminalStatus.active
        assert resp.closed_at is None

    def test_closed_session(self):
        resp = TerminalSessionResponse(
            id=2,
            site_code="SITE01",
            staff_id="STAFF-002",
            terminal_name="Terminal-2",
            status=TerminalStatus.closed,
            opened_at=NOW,
            closed_at=NOW,
            opening_cash=Decimal("0"),
            closing_cash=Decimal("850.0000"),
        )
        assert resp.status == TerminalStatus.closed
        assert resp.closing_cash == Decimal("850.0000")


# ---------------------------------------------------------------------------
# CheckoutRequest / CheckoutResponse
# ---------------------------------------------------------------------------


class TestCheckout:
    def test_cash_checkout_request(self):
        req = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("200.0000"),
        )
        assert req.payment_method == PaymentMethod.cash
        assert req.transaction_discount == Decimal("0")

    def test_insurance_checkout_request(self):
        req = CheckoutRequest(
            payment_method=PaymentMethod.insurance,
            insurance_no="INS-12345",
            customer_id="CUST-001",
        )
        assert req.insurance_no == "INS-12345"

    def test_checkout_response(self):
        resp = CheckoutResponse(
            transaction_id=42,
            receipt_number="RCT-20260415-0001",
            grand_total=Decimal("135.5000"),
            payment_method=PaymentMethod.cash,
            change_due=Decimal("64.5000"),
            status=TransactionStatus.completed,
        )
        assert resp.change_due == Decimal("64.5000")
        assert resp.status == TransactionStatus.completed

    def test_checkout_response_frozen(self):
        resp = CheckoutResponse(
            transaction_id=1,
            receipt_number="R-001",
            grand_total=Decimal("100"),
            payment_method=PaymentMethod.cash,
            status=TransactionStatus.completed,
        )
        with pytest.raises(ValidationError):
            resp.grand_total = Decimal("999")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AddItemRequest / UpdateItemRequest
# ---------------------------------------------------------------------------


class TestItemRequests:
    def test_add_item(self):
        req = AddItemRequest(drug_code="DRUG001", quantity=Decimal("3"))
        assert req.quantity == Decimal("3")
        assert req.override_price is None

    def test_add_item_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            AddItemRequest(drug_code="DRUG001", quantity=Decimal("0"))

    def test_add_item_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            AddItemRequest(drug_code="DRUG001", quantity=Decimal("-1"))

    def test_update_item(self):
        req = UpdateItemRequest(quantity=Decimal("5"), discount=Decimal("10.0000"))
        assert req.discount == Decimal("10.0000")


# ---------------------------------------------------------------------------
# VoidRequest
# ---------------------------------------------------------------------------


class TestVoidRequest:
    def test_valid(self):
        req = VoidRequest(reason="Customer changed mind after payment.")
        assert req.reason.startswith("Customer")

    def test_too_short_rejected(self):
        with pytest.raises(ValidationError):
            VoidRequest(reason="OK")  # min_length=3


# ---------------------------------------------------------------------------
# ReturnRequest / ReturnResponse / ReturnDetailResponse
# ---------------------------------------------------------------------------


class TestReturns:
    def _make_item(self) -> PosCartItem:
        return PosCartItem(
            drug_code="DRUG001",
            drug_name="Panadol",
            quantity=Decimal("1"),
            unit_price=Decimal("25"),
            line_total=Decimal("25"),
        )

    def test_return_request(self):
        req = ReturnRequest(
            original_transaction_id=10,
            items=[self._make_item()],
            reason=ReturnReason.defective,
            refund_method="cash",
        )
        assert req.reason == ReturnReason.defective
        assert len(req.items) == 1

    def test_invalid_refund_method(self):
        with pytest.raises(ValidationError):
            ReturnRequest(
                original_transaction_id=10,
                items=[self._make_item()],
                reason=ReturnReason.expired,
                refund_method="wallet",  # not allowed
            )

    def test_return_response(self):
        resp = ReturnResponse(
            id=1,
            original_transaction_id=10,
            refund_amount=Decimal("25.0000"),
            refund_method="cash",
            reason=ReturnReason.defective,
            created_at=NOW,
        )
        assert resp.refund_amount == Decimal("25.0000")


# ---------------------------------------------------------------------------
# ShiftSummaryResponse / CashCountRequest / CashDrawerEventResponse
# ---------------------------------------------------------------------------


class TestShift:
    def test_shift_summary(self):
        resp = ShiftSummaryResponse(
            id=1,
            terminal_id=1,
            staff_id="STAFF-001",
            shift_date=TODAY,
            opened_at=NOW,
            opening_cash=Decimal("500.0000"),
            transaction_count=12,
            total_sales=Decimal("1250.7500"),
        )
        assert resp.transaction_count == 12
        assert resp.variance is None

    def test_cash_count_request(self):
        req = CashCountRequest(
            event_type=CashDrawerEventType.sale,
            amount=Decimal("135.5000"),
        )
        assert req.event_type == CashDrawerEventType.sale

    def test_cash_drawer_event_response(self):
        resp = CashDrawerEventResponse(
            id=5,
            terminal_id=1,
            event_type=CashDrawerEventType.pickup,
            amount=Decimal("300.0000"),
            timestamp=NOW,
        )
        assert resp.event_type == CashDrawerEventType.pickup


# ---------------------------------------------------------------------------
# PosProductResult / PosStockInfo / BatchSummary
# ---------------------------------------------------------------------------


class TestProductSearch:
    def test_product_result(self):
        result = PosProductResult(
            drug_code="DRUG001",
            drug_name="Panadol Extra 500mg",
            unit_price=Decimal("25.0000"),
            stock_quantity=Decimal("150.0000"),
        )
        assert result.is_controlled is False
        assert result.requires_pharmacist is False

    def test_stock_info_with_batches(self):
        batch = BatchSummary(
            batch_number="BATCH-001",
            expiry_date=date(2027, 6, 15),
            quantity_available=Decimal("100.0000"),
        )
        info = PosStockInfo(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_available=Decimal("100.0000"),
            batches=[batch],
        )
        assert len(info.batches) == 1
        assert info.batches[0].expiry_date == date(2027, 6, 15)


# ---------------------------------------------------------------------------
# EmailReceiptRequest
# ---------------------------------------------------------------------------


class TestEmailReceiptRequest:
    def test_valid_email(self):
        req = EmailReceiptRequest(email="customer@example.com")
        assert req.email == "customer@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            EmailReceiptRequest(email="not-an-email")


# ---------------------------------------------------------------------------
# PharmacistVerifyRequest
# ---------------------------------------------------------------------------


class TestPharmacistVerifyRequest:
    def test_valid(self):
        req = PharmacistVerifyRequest(
            pharmacist_id="PHARM-001",
            credential="secure-pin-1234",
            drug_code="DRUG999",
        )
        assert req.pharmacist_id == "PHARM-001"

    def test_short_credential_rejected(self):
        with pytest.raises(ValidationError):
            PharmacistVerifyRequest(
                pharmacist_id="PHARM-001",
                credential="abc",  # min_length=4
                drug_code="DRUG999",
            )


# ---------------------------------------------------------------------------
# Enum value tests
# ---------------------------------------------------------------------------


class TestEnumValues:
    def test_transaction_status_values(self):
        assert TransactionStatus.draft == "draft"
        assert TransactionStatus.completed == "completed"
        assert TransactionStatus.voided == "voided"
        assert TransactionStatus.returned == "returned"

    def test_terminal_status_values(self):
        assert TerminalStatus.open == "open"
        assert TerminalStatus.active == "active"
        assert TerminalStatus.paused == "paused"
        assert TerminalStatus.closed == "closed"

    def test_payment_method_values(self):
        assert PaymentMethod.cash == "cash"
        assert PaymentMethod.card == "card"
        assert PaymentMethod.insurance == "insurance"
        assert PaymentMethod.voucher == "voucher"
        assert PaymentMethod.mixed == "mixed"

    def test_return_reason_values(self):
        assert ReturnReason.defective == "defective"
        assert ReturnReason.wrong_drug == "wrong_drug"
        assert ReturnReason.expired == "expired"
        assert ReturnReason.customer_request == "customer_request"

    def test_receipt_format_values(self):
        assert ReceiptFormat.thermal == "thermal"
        assert ReceiptFormat.pdf == "pdf"
        assert ReceiptFormat.email == "email"
