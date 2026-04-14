"""Unit tests for PurchaseOrderService business logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi import HTTPException

from datapulse.purchase_orders.models import (
    POCreateLineRequest,
    POCreateRequest,
    POReceiveLineRequest,
    POReceiveRequest,
    POUpdateRequest,
    PurchaseOrder,
)
from datapulse.purchase_orders.repository import PurchaseOrderRepository
from datapulse.purchase_orders.service import PurchaseOrderService


def _make_po(**overrides) -> PurchaseOrder:
    defaults = dict(
        po_number="PO-1-20250115-0001",
        po_date=date(2025, 1, 15),
        supplier_code="SUP001",
        site_code="SITE01",
        status="draft",
        total_ordered_value=Decimal("100.00"),
        total_received_value=Decimal("0"),
        line_count=1,
    )
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


@pytest.fixture()
def mock_po_repo():
    return create_autospec(PurchaseOrderRepository, instance=True)


@pytest.fixture()
def po_service(mock_po_repo):
    return PurchaseOrderService(mock_po_repo)


class TestListPOs:
    def test_delegates_to_repo(self, po_service, mock_po_repo):
        mock_po_repo.list_pos.return_value = MagicMock(items=[], total=0)
        result = po_service.list_pos(tenant_id=1)
        mock_po_repo.list_pos.assert_called_once()
        assert result.total == 0

    def test_invalid_status_raises_422(self, po_service, mock_po_repo):
        with pytest.raises(HTTPException) as exc_info:
            po_service.list_pos(tenant_id=1, status="BOGUS")
        assert exc_info.value.status_code == 422


class TestGetPO:
    def test_found(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = _make_po()
        result = po_service.get_po("PO-1-20250115-0001", 1)
        assert result.po_number == "PO-1-20250115-0001"

    def test_not_found_raises_404(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            po_service.get_po("MISSING", 1)
        assert exc_info.value.status_code == 404


class TestCreatePO:
    def test_creates_and_returns(self, po_service, mock_po_repo):
        expected = _make_po()
        mock_po_repo.create_po.return_value = expected

        req = POCreateRequest(
            po_date=date(2025, 1, 15),
            supplier_code="SUP001",
            site_code="SITE01",
            lines=[
                POCreateLineRequest(drug_code="D1", quantity=Decimal("10"), unit_price=Decimal("5"))
            ],
        )
        result = po_service.create_po(req, tenant_id=1, created_by="test-user")
        assert result.po_number == "PO-1-20250115-0001"
        mock_po_repo.create_po.assert_called_once()


class TestUpdatePO:
    def test_updates_draft_po(self, po_service, mock_po_repo):
        existing = _make_po(status="draft")
        updated = _make_po(status="submitted")
        mock_po_repo.get_po.return_value = existing
        mock_po_repo.update_po.return_value = updated

        result = po_service.update_po("PO-1-20250115-0001", 1, POUpdateRequest(status="submitted"))
        assert result.status == "submitted"

    def test_cannot_update_received_po(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = _make_po(status="received")
        with pytest.raises(HTTPException) as exc_info:
            po_service.update_po("PO-1-20250115-0001", 1, POUpdateRequest(notes="test"))
        assert exc_info.value.status_code == 409

    def test_cannot_update_cancelled_po(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = _make_po(status="cancelled")
        with pytest.raises(HTTPException) as exc_info:
            po_service.update_po("PO-1-20250115-0001", 1, POUpdateRequest(notes="test"))
        assert exc_info.value.status_code == 409

    def test_not_found_raises_404(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            po_service.update_po("MISSING", 1, POUpdateRequest())
        assert exc_info.value.status_code == 404


class TestReceivePO:
    def _make_receive_req(self, po_number="PO-1-20250115-0001"):
        return POReceiveRequest(
            po_number=po_number,
            lines=[
                POReceiveLineRequest(
                    line_number=1,
                    received_quantity=Decimal("10"),
                    batch_number="BATCH001",
                    expiry_date=date(2026, 12, 31),
                ),
            ],
        )

    def test_receive_creates_stock_receipts(self, po_service, mock_po_repo):
        """Critical test: receive_po must call insert_stock_receipts."""
        po_number = "PO-1-20250115-0001"
        mock_po_repo.get_po.return_value = _make_po(status="submitted")
        mock_po_repo.get_line_details_map.return_value = {
            1: POCreateLineRequest(
                drug_code="D1", quantity=Decimal("10"), unit_price=Decimal("5.50")
            ),
        }
        mock_po_repo.receive_po_lines.return_value = None
        mock_po_repo.insert_stock_receipts.return_value = 1
        mock_po_repo.recalculate_po_status.return_value = "received"
        mock_po_repo.get_po.side_effect = [
            _make_po(status="submitted"),  # first call in receive_po
            _make_po(status="received"),  # final get_po after update
        ]

        req = self._make_receive_req(po_number)
        result = po_service.receive_po(req, tenant_id=1)

        # CRITICAL: stock receipts MUST be inserted
        mock_po_repo.insert_stock_receipts.assert_called_once()
        # Status must be recalculated
        mock_po_repo.recalculate_po_status.assert_called_once_with(po_number, 1)
        assert result.status == "received"

    def test_cannot_receive_cancelled_po(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = _make_po(status="cancelled")
        with pytest.raises(HTTPException) as exc_info:
            po_service.receive_po(self._make_receive_req(), tenant_id=1)
        assert exc_info.value.status_code == 409

    def test_cannot_receive_already_received_po(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = _make_po(status="received")
        with pytest.raises(HTTPException) as exc_info:
            po_service.receive_po(self._make_receive_req(), tenant_id=1)
        assert exc_info.value.status_code == 409

    def test_not_found_raises_404(self, po_service, mock_po_repo):
        mock_po_repo.get_po.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            po_service.receive_po(self._make_receive_req(), tenant_id=1)
        assert exc_info.value.status_code == 404


class TestCancelPO:
    def test_cancel_draft_po(self, po_service, mock_po_repo):
        mock_po_repo.cancel_po.return_value = _make_po(status="cancelled")
        result = po_service.cancel_po("PO-001", 1)
        assert result.status == "cancelled"

    def test_cancel_not_found_raises_404(self, po_service, mock_po_repo):
        mock_po_repo.cancel_po.return_value = None
        mock_po_repo.get_po.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            po_service.cancel_po("MISSING", 1)
        assert exc_info.value.status_code == 404

    def test_cancel_received_raises_409(self, po_service, mock_po_repo):
        mock_po_repo.cancel_po.return_value = None
        mock_po_repo.get_po.return_value = _make_po(status="received")
        with pytest.raises(HTTPException) as exc_info:
            po_service.cancel_po("PO-001", 1)
        assert exc_info.value.status_code == 409
