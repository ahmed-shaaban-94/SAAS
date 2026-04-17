"""Unit tests for PurchaseOrderRepository using a mocked SQLAlchemy session."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.purchase_orders.models import POCreateLineRequest, POReceiveLineRequest
from datapulse.purchase_orders.repository import PurchaseOrderRepository


@pytest.fixture()
def mock_session():
    return MagicMock()


@pytest.fixture()
def po_repo(mock_session):
    return PurchaseOrderRepository(mock_session)


class TestListPOs:
    def test_returns_empty_list(self, po_repo, mock_session):
        # count query
        mock_session.execute.return_value.scalar_one.return_value = 0
        # select query
        mock_session.execute.return_value.fetchall.return_value = []

        result = po_repo.list_pos(tenant_id=1)
        assert result.total == 0
        assert result.items == []
        assert result.offset == 0
        assert result.limit == 20


class TestGetPO:
    def test_returns_none_when_not_found(self, po_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = None
        result = po_repo.get_po("MISSING", 1)
        assert result is None


class TestRecalculateStatus:
    def _mock_qty_result(self, session, total_ordered, total_received):
        mock_row = MagicMock()
        mock_row._mapping = {
            "total_ordered": total_ordered,
            "total_received": total_received,
        }
        session.execute.return_value.fetchone.return_value = mock_row

    def test_fully_received(self, po_repo, mock_session):
        self._mock_qty_result(mock_session, 10, 10)
        result = po_repo.recalculate_po_status("PO-001", 1)
        assert result == "received"

    def test_partial_delivery(self, po_repo, mock_session):
        self._mock_qty_result(mock_session, 10, 5)
        result = po_repo.recalculate_po_status("PO-001", 1)
        assert result == "partial"

    def test_zero_received_becomes_submitted(self, po_repo, mock_session):
        self._mock_qty_result(mock_session, 10, 0)
        result = po_repo.recalculate_po_status("PO-001", 1)
        assert result == "submitted"

    def test_no_lines_returns_draft(self, po_repo, mock_session):
        mock_session.execute.return_value.fetchone.return_value = None
        result = po_repo.recalculate_po_status("PO-001", 1)
        assert result == "draft"


class TestInsertStockReceipts:
    def test_inserts_one_row_per_valid_line(self, po_repo, mock_session):
        mock_session.execute.return_value = MagicMock()

        lines = [
            POReceiveLineRequest(
                line_number=1,
                received_quantity=Decimal("5"),
                batch_number="B001",
                expiry_date=date(2026, 12, 31),
            ),
            POReceiveLineRequest(
                line_number=2,
                received_quantity=Decimal("0"),  # zero — should NOT be inserted
            ),
        ]
        line_details = {
            1: POCreateLineRequest(drug_code="D1", quantity=Decimal("10"), unit_price=Decimal("5")),
        }

        count = po_repo.insert_stock_receipts(
            po_number="PO-001",
            tenant_id=1,
            site_code="SITE01",
            receipt_date=date(2025, 1, 15),
            lines=lines,
            line_details=line_details,
        )
        # Only line 1 has received_quantity > 0
        assert count == 1

    def test_zero_received_lines_skipped(self, po_repo, mock_session):
        lines = [
            POReceiveLineRequest(line_number=1, received_quantity=Decimal("0")),
        ]
        count = po_repo.insert_stock_receipts(
            po_number="PO-001",
            tenant_id=1,
            site_code="SITE01",
            receipt_date=date(2025, 1, 15),
            lines=lines,
            line_details={},
        )
        assert count == 0
        # execute should not have been called for insert
