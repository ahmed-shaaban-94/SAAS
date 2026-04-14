"""Unit tests for purchase_orders Pydantic models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datapulse.purchase_orders.models import (
    VALID_PO_STATUSES,
    POCreateLineRequest,
    POCreateRequest,
    POReceiveLineRequest,
    POReceiveRequest,
    POUpdateRequest,
    PurchaseOrder,
)


class TestPOCreateRequest:
    def test_valid(self):
        req = POCreateRequest(
            po_date=date(2025, 1, 15),
            supplier_code="SUP001",
            site_code="SITE01",
            lines=[
                POCreateLineRequest(
                    drug_code="DRUG001", quantity=Decimal("10"), unit_price=Decimal("5.50")
                )
            ],
        )
        assert req.supplier_code == "SUP001"
        assert len(req.lines) == 1

    def test_empty_lines_rejected(self):
        with pytest.raises(ValidationError):
            POCreateRequest(
                po_date=date(2025, 1, 15),
                supplier_code="SUP001",
                site_code="SITE01",
                lines=[],
            )

    def test_empty_supplier_code_stripped(self):
        with pytest.raises(ValidationError):
            POCreateRequest(
                po_date=date(2025, 1, 15),
                supplier_code="  ",
                site_code="SITE01",
                lines=[
                    POCreateLineRequest(
                        drug_code="D1", quantity=Decimal("1"), unit_price=Decimal("1")
                    )
                ],
            )

    def test_line_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            POCreateLineRequest(drug_code="D1", quantity=Decimal("0"), unit_price=Decimal("5"))

    def test_line_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            POCreateLineRequest(drug_code="D1", quantity=Decimal("5"), unit_price=Decimal("-1"))


class TestPOUpdateRequest:
    def test_valid_status(self):
        req = POUpdateRequest(status="submitted")
        assert req.status == "submitted"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            POUpdateRequest(status="BOGUS")

    def test_all_none_is_valid(self):
        req = POUpdateRequest()
        assert req.status is None
        assert req.notes is None
        assert req.expected_date is None

    def test_all_valid_statuses(self):
        for status in VALID_PO_STATUSES:
            req = POUpdateRequest(status=status)
            assert req.status == status


class TestPOReceiveRequest:
    def test_valid(self):
        req = POReceiveRequest(
            po_number="PO-1-20250115-0001",
            lines=[
                POReceiveLineRequest(line_number=1, received_quantity=Decimal("5")),
            ],
        )
        assert req.po_number == "PO-1-20250115-0001"
        assert req.lines[0].received_quantity == Decimal("5")

    def test_empty_lines_rejected(self):
        with pytest.raises(ValidationError):
            POReceiveRequest(po_number="PO-001", lines=[])

    def test_negative_received_qty_rejected(self):
        with pytest.raises(ValidationError):
            POReceiveLineRequest(line_number=1, received_quantity=Decimal("-1"))


class TestPurchaseOrderModel:
    def test_immutable(self):
        from pydantic import ValidationError as PydanticValidationError

        po = PurchaseOrder(
            po_number="PO-001",
            po_date=date(2025, 1, 1),
            supplier_code="S1",
            site_code="SITE1",
            status="draft",
        )
        # Frozen Pydantic models raise ValidationError / TypeError on attribute set
        with pytest.raises((PydanticValidationError, TypeError, AttributeError)):
            po.status = "received"  # type: ignore[misc]

    def test_defaults(self):
        po = PurchaseOrder(
            po_number="PO-001",
            po_date=date(2025, 1, 1),
            supplier_code="S1",
            site_code="SITE1",
            status="draft",
        )
        assert po.total_ordered_value == Decimal("0")
        assert po.line_count == 0
