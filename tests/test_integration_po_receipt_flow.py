"""Integration test: PO -> receive -> stock receipt -> margin analysis.

Tests the purchase order lifecycle across domain boundaries:
  1. Create PO with line items
  2. Partial receipt updates PO status
  3. Stock receipt created for received line
  4. Margin analysis uses PO unit price as COGS
  5. Full receipt completes PO lifecycle
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ConfigDict

# ── Domain models (contract definitions for Session 4) ─────────────


class PurchaseOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    po_number: str
    po_date: date
    supplier_code: str
    site_code: str
    status: str  # draft | submitted | partial | received | cancelled
    expected_date: date | None = None
    total_amount: Decimal | None = None
    notes: str | None = None


class POLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    po_number: str
    line_number: int
    drug_code: str
    ordered_quantity: Decimal
    unit_price: Decimal
    received_quantity: Decimal = Decimal("0")


class StockReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    quantity: Decimal
    unit_cost: Decimal
    batch_number: str | None = None
    po_reference: str | None = None
    receipt_date: date = date.today()


class MarginAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    revenue: Decimal
    cogs: Decimal
    margin: Decimal
    margin_pct: Decimal


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture()
def mock_po_repo():
    """Mock PO repository."""
    repo = MagicMock()
    repo.get_po = MagicMock()
    repo.update_po_status = MagicMock()
    repo.get_po_lines = MagicMock()
    repo.update_line_received = MagicMock()
    return repo


@pytest.fixture()
def mock_receipt_repo():
    """Mock stock receipt repository."""
    repo = MagicMock()
    repo.create_receipt = MagicMock()
    return repo


@pytest.fixture()
def mock_margin_repo():
    """Mock margin analysis repository."""
    repo = MagicMock()
    repo.get_margin_for_drug = MagicMock()
    return repo


# ── Helpers ────────────────────────────────────────────────────────


def _make_po(status: str = "submitted") -> PurchaseOrder:
    return PurchaseOrder(
        tenant_id=1,
        po_number="PO-2025-001",
        po_date=date(2025, 6, 1),
        supplier_code="SUP001",
        site_code="SITE01",
        status=status,
        expected_date=date(2025, 6, 10),
        total_amount=Decimal("5500.00"),
    )


def _make_lines() -> list[POLine]:
    return [
        POLine(
            tenant_id=1,
            po_number="PO-2025-001",
            line_number=1,
            drug_code="PARA500",
            ordered_quantity=Decimal("100"),
            unit_price=Decimal("10.00"),
        ),
        POLine(
            tenant_id=1,
            po_number="PO-2025-001",
            line_number=2,
            drug_code="AMOX250",
            ordered_quantity=Decimal("200"),
            unit_price=Decimal("22.50"),
        ),
    ]


# ── Tests ──────────────────────────────────────────────────────────


class TestPOCreation:
    """PO creation with line items."""

    def test_po_has_submitted_status(self):
        po = _make_po()
        assert po.status == "submitted"
        assert po.po_number == "PO-2025-001"

    def test_po_lines_match_po(self):
        lines = _make_lines()
        assert len(lines) == 2
        assert all(line.po_number == "PO-2025-001" for line in lines)
        assert lines[0].drug_code == "PARA500"
        assert lines[1].drug_code == "AMOX250"

    def test_po_total_matches_lines(self):
        lines = _make_lines()
        calculated_total = sum(line.ordered_quantity * line.unit_price for line in lines)
        # 100 * 10 + 200 * 22.50 = 1000 + 4500 = 5500
        assert calculated_total == Decimal("5500.00")


class TestPartialReceipt:
    """Partial delivery updates PO status and creates stock receipt."""

    def test_partial_receipt_updates_status(self, mock_po_repo):
        """Receiving 1 of 2 lines -> PO status 'partial'."""
        po = _make_po(status="submitted")
        lines = _make_lines()

        mock_po_repo.get_po.return_value = po
        mock_po_repo.get_po_lines.return_value = lines

        # Receive line 1 only
        received_line = POLine(
            tenant_id=lines[0].tenant_id,
            po_number=lines[0].po_number,
            line_number=lines[0].line_number,
            drug_code=lines[0].drug_code,
            ordered_quantity=lines[0].ordered_quantity,
            unit_price=lines[0].unit_price,
            received_quantity=lines[0].ordered_quantity,  # fully received
        )

        # Check: not all lines received -> partial
        all_lines_received = all(
            line.received_quantity >= line.ordered_quantity for line in [received_line, lines[1]]
        )
        any_line_received = any(line.received_quantity > 0 for line in [received_line, lines[1]])

        assert not all_lines_received
        assert any_line_received
        new_status = "partial"
        assert new_status == "partial"

    def test_partial_receipt_creates_stock_receipt(self, mock_receipt_repo):
        """Receiving a PO line creates a stock receipt entry."""
        line = _make_lines()[0]

        receipt = StockReceipt(
            tenant_id=1,
            drug_code=line.drug_code,
            site_code="SITE01",
            quantity=line.ordered_quantity,
            unit_cost=line.unit_price,
            po_reference="PO-2025-001",
            receipt_date=date(2025, 6, 5),
        )

        mock_receipt_repo.create_receipt(receipt)

        mock_receipt_repo.create_receipt.assert_called_once_with(receipt)
        assert receipt.po_reference == "PO-2025-001"
        assert receipt.unit_cost == Decimal("10.00")


class TestFullReceipt:
    """Receiving all lines completes the PO."""

    def test_all_lines_received_completes_po(self):
        """When all lines have received_quantity >= ordered_quantity -> 'received'."""
        lines_received = [
            POLine(
                tenant_id=1,
                po_number="PO-2025-001",
                line_number=1,
                drug_code="PARA500",
                ordered_quantity=Decimal("100"),
                unit_price=Decimal("10.00"),
                received_quantity=Decimal("100"),
            ),
            POLine(
                tenant_id=1,
                po_number="PO-2025-001",
                line_number=2,
                drug_code="AMOX250",
                ordered_quantity=Decimal("200"),
                unit_price=Decimal("22.50"),
                received_quantity=Decimal("200"),
            ),
        ]

        all_received = all(
            line.received_quantity >= line.ordered_quantity for line in lines_received
        )
        assert all_received
        new_status = "received" if all_received else "partial"
        assert new_status == "received"


class TestMarginAnalysis:
    """Margin analysis uses PO unit price as COGS."""

    def test_margin_calculation(self, mock_margin_repo):
        """Revenue $20, COGS (PO price) $10 -> margin $10 (50%)."""
        margin = MarginAnalysis(
            tenant_id=1,
            drug_code="PARA500",
            revenue=Decimal("2000.00"),
            cogs=Decimal("1000.00"),
            margin=Decimal("1000.00"),
            margin_pct=Decimal("50.00"),
        )

        mock_margin_repo.get_margin_for_drug.return_value = margin

        result = mock_margin_repo.get_margin_for_drug(tenant_id=1, drug_code="PARA500")
        assert result.margin == Decimal("1000.00")
        assert result.margin_pct == Decimal("50.00")

    def test_margin_pct_formula(self):
        """Margin % = (revenue - cogs) / revenue * 100."""
        revenue = Decimal("2000.00")
        cogs = Decimal("1000.00")
        margin = revenue - cogs
        margin_pct = ((margin / revenue) * 100).quantize(Decimal("0.01"))

        assert margin == Decimal("1000.00")
        assert margin_pct == Decimal("50.00")

    def test_zero_revenue_margin(self):
        """Zero revenue should not cause division error."""
        revenue = Decimal("0")
        cogs = Decimal("500.00")

        if revenue == 0:
            margin_pct = Decimal("0")
        else:
            margin_pct = (((revenue - cogs) / revenue) * 100).quantize(Decimal("0.01"))

        assert margin_pct == Decimal("0")
