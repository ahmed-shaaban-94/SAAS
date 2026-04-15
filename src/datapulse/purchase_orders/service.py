"""Business logic layer for purchase orders.

Service enforces business rules and orchestrates the critical
PO receive → stock receipts flow that feeds into inventory.
"""

from __future__ import annotations

from datetime import date

import structlog
from fastapi import HTTPException

from datapulse.purchase_orders.models import (
    VALID_PO_STATUSES,
    MarginAnalysisList,
    POCreateRequest,
    POLineList,
    POList,
    POReceiveRequest,
    POUpdateRequest,
    PurchaseOrder,
    PurchaseOrderDetail,
)
from datapulse.purchase_orders.repository import PurchaseOrderRepository

log = structlog.get_logger(__name__)


class PurchaseOrderService:
    """Business logic for PO lifecycle management."""

    def __init__(self, repo: PurchaseOrderRepository) -> None:
        self._repo = repo

    def list_pos(
        self,
        *,
        tenant_id: int,
        status: str | None = None,
        supplier_code: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> POList:
        if status is not None and status not in VALID_PO_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid status '{status}'. "
                    f"Must be one of: {', '.join(sorted(VALID_PO_STATUSES))}"
                ),
            )
        return self._repo.list_pos(
            tenant_id=tenant_id,
            status=status,
            supplier_code=supplier_code,
            offset=offset,
            limit=limit,
        )

    def get_po(self, po_number: str, tenant_id: int) -> PurchaseOrder:
        po = self._repo.get_po(po_number, tenant_id)
        if po is None:
            raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found")
        return po

    def get_po_detail(self, po_number: str, tenant_id: int) -> PurchaseOrderDetail:
        po = self._repo.get_po_detail(po_number, tenant_id)
        if po is None:
            raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found")
        return po

    def get_lines(self, po_number: str, tenant_id: int) -> POLineList:
        po = self._repo.get_po(po_number, tenant_id)
        if po is None:
            raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found")
        lines = self._repo.get_lines(po_number, tenant_id)
        return POLineList(po_number=po_number, lines=lines, total=len(lines))

    def create_po(
        self,
        data: POCreateRequest,
        tenant_id: int,
        created_by: str | None = None,
    ) -> PurchaseOrder:
        if not data.lines:
            raise HTTPException(
                status_code=422,
                detail="A purchase order must have at least one line",
            )
        return self._repo.create_po(data, tenant_id, created_by=created_by)

    def update_po(
        self,
        po_number: str,
        tenant_id: int,
        data: POUpdateRequest,
    ) -> PurchaseOrder:
        existing = self._repo.get_po(po_number, tenant_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found")

        # Only allow updates on non-final POs
        if existing.status in ("received", "cancelled"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot update a PO with status '{existing.status}'",
            )

        result = self._repo.update_po(
            po_number,
            tenant_id,
            expected_date=data.expected_date,
            notes=data.notes,
            status=data.status,
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found")
        return result

    def receive_po(
        self,
        data: POReceiveRequest,
        tenant_id: int,
        site_code: str | None = None,
        receipt_date: date | None = None,
    ) -> PurchaseOrder:
        """Record a PO delivery.

        1. Validates PO exists and is receivable (not cancelled/already fully received).
        2. Updates received_quantity on each line.
        3. Creates bronze.stock_receipts entries — this is the critical step that
           feeds into fct_stock_movements via the dbt silver pipeline.
        4. Recalculates and persists the PO status (partial / received).
        """
        po = self._repo.get_po(data.po_number, tenant_id)
        if po is None:
            raise HTTPException(
                status_code=404, detail=f"Purchase order '{data.po_number}' not found"
            )
        if po.status == "cancelled":
            raise HTTPException(
                status_code=409,
                detail="Cannot receive a cancelled purchase order",
            )
        if po.status == "received":
            raise HTTPException(
                status_code=409,
                detail="Purchase order is already fully received",
            )

        effective_site = site_code or po.site_code
        effective_date = receipt_date or date.today()

        # Get line details map for stock receipt creation
        line_details_map = self._repo.get_line_details_map(data.po_number, tenant_id)

        # 1. Update received_quantity on PO lines
        self._repo.receive_po_lines(data.po_number, tenant_id, data.lines)

        # 2. Create stock receipt entries (feeds inventory pipeline)
        receipts_inserted = self._repo.insert_stock_receipts(
            po_number=data.po_number,
            tenant_id=tenant_id,
            site_code=effective_site,
            receipt_date=effective_date,
            lines=data.lines,
            line_details=line_details_map,
        )
        log.info(
            "po_receive_stock_receipts_created",
            po_number=data.po_number,
            tenant_id=tenant_id,
            receipts_inserted=receipts_inserted,
        )

        # 3. Recalculate PO status
        new_status = self._repo.recalculate_po_status(data.po_number, tenant_id)
        log.info(
            "po_receive_complete",
            po_number=data.po_number,
            tenant_id=tenant_id,
            new_status=new_status,
        )

        result = self._repo.get_po(data.po_number, tenant_id)
        assert result is not None
        return result

    def cancel_po(self, po_number: str, tenant_id: int) -> PurchaseOrder:
        result = self._repo.cancel_po(po_number, tenant_id)
        if result is None:
            # Could be not found OR not in a cancellable state
            existing = self._repo.get_po(po_number, tenant_id)
            if existing is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Purchase order '{po_number}' not found",
                )
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel a PO with status '{existing.status}'",
            )
        return result

    def get_margin_analysis(
        self,
        *,
        tenant_id: int,
        year: int | None = None,
        month: int | None = None,
        drug_code: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> MarginAnalysisList:
        return self._repo.get_margin_analysis(
            tenant_id=tenant_id,
            year=year,
            month=month,
            drug_code=drug_code,
            offset=offset,
            limit=limit,
        )
