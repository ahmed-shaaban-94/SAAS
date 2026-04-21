"""Data-access layer for purchase orders and margin analysis.

All SQL uses parameterized queries via SQLAlchemy text() — no f-string
interpolation of user-supplied values.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.core.sql import build_where_eq
from datapulse.purchase_orders.models import (
    MarginAnalysisList,
    MarginAnalysisRow,
    POCreateLineRequest,
    POCreateRequest,
    POLineItem,
    POList,
    POReceiveLineRequest,
    PurchaseOrder,
    PurchaseOrderDetail,
)

log = structlog.get_logger(__name__)

_SAFE_COL_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# ── Helpers ──────────────────────────────────────────────────────────────────


def _dec(v) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(v))


def _row_to_po(row) -> PurchaseOrder:
    m = row._mapping
    return PurchaseOrder(
        po_number=m["po_number"],
        po_date=m["po_date"],
        supplier_code=m["supplier_code"],
        supplier_name=m.get("supplier_name"),
        site_code=m["site_code"],
        status=m["status"],
        expected_date=m.get("expected_date"),
        total_ordered_value=_dec(m.get("total_ordered_value")) or Decimal("0"),
        total_received_value=_dec(m.get("total_received_value")) or Decimal("0"),
        line_count=int(m.get("line_count") or 0),
        notes=m.get("notes"),
        created_by=m.get("created_by"),
    )


def _row_to_line(row) -> POLineItem:
    m = row._mapping
    return POLineItem(
        line_number=int(m["line_number"]),
        drug_code=m["drug_code"],
        drug_name=m.get("drug_name"),
        ordered_quantity=_dec(m["ordered_quantity"]) or Decimal("0"),
        unit_price=_dec(m["unit_price"]) or Decimal("0"),
        received_quantity=_dec(m.get("received_quantity")) or Decimal("0"),
        line_total=_dec(m.get("line_total")) or Decimal("0"),
        fulfillment_pct=_dec(m.get("fulfillment_pct")),
    )


class PurchaseOrderRepository:
    """Thin data-access layer for purchase order operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── List / Read ───────────────────────────────────────────────────────

    def list_pos(
        self,
        *,
        tenant_id: int,
        status: str | None = None,
        supplier_code: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> POList:
        where, params = build_where_eq(
            [
                ("po.tenant_id", "tenant_id", tenant_id),
                ("po.status", "status", status),
                ("po.supplier_code", "supplier_code", supplier_code),
            ]
        )
        params["limit"] = limit
        params["offset"] = offset

        count_stmt = text(f"SELECT COUNT(*) FROM bronze.purchase_orders po WHERE {where}")
        total = self._session.execute(count_stmt, params).scalar_one()

        # Join with lines aggregate for totals
        select_stmt = text(f"""
            SELECT
                po.po_number, po.po_date, po.supplier_code, po.site_code,
                po.status, po.expected_date, po.notes, po.created_by,
                COALESCE(la.total_ordered_value, 0)  AS total_ordered_value,
                COALESCE(la.total_received_value, 0) AS total_received_value,
                COALESCE(la.line_count, 0)           AS line_count
            FROM bronze.purchase_orders po
            LEFT JOIN (
                SELECT
                    tenant_id,
                    po_number,
                    SUM(ordered_quantity * unit_price)  AS total_ordered_value,
                    SUM(received_quantity * unit_price) AS total_received_value,
                    COUNT(*)                            AS line_count
                FROM bronze.po_lines
                WHERE tenant_id = :tenant_id
                GROUP BY tenant_id, po_number
            ) la ON po.po_number = la.po_number
            WHERE {where}
            ORDER BY po.po_date DESC, po.po_number
            LIMIT :limit OFFSET :offset
        """)
        rows = self._session.execute(select_stmt, params).fetchall()
        return POList(
            items=[_row_to_po(r) for r in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_po(self, po_number: str, tenant_id: int) -> PurchaseOrder | None:
        stmt = text("""
            SELECT
                po.po_number, po.po_date, po.supplier_code, po.site_code,
                po.status, po.expected_date, po.notes, po.created_by,
                COALESCE(la.total_ordered_value, 0)  AS total_ordered_value,
                COALESCE(la.total_received_value, 0) AS total_received_value,
                COALESCE(la.line_count, 0)           AS line_count
            FROM bronze.purchase_orders po
            LEFT JOIN (
                SELECT
                    tenant_id,
                    po_number,
                    SUM(ordered_quantity * unit_price)  AS total_ordered_value,
                    SUM(received_quantity * unit_price) AS total_received_value,
                    COUNT(*)                            AS line_count
                FROM bronze.po_lines
                WHERE tenant_id = :tenant_id AND po_number = :po_number
                GROUP BY tenant_id, po_number
            ) la ON po.po_number = la.po_number
            WHERE po.tenant_id = :tenant_id AND po.po_number = :po_number
        """)
        params = {"tenant_id": tenant_id, "po_number": po_number}
        row = self._session.execute(stmt, params).fetchone()
        return _row_to_po(row) if row else None

    def get_po_detail(self, po_number: str, tenant_id: int) -> PurchaseOrderDetail | None:
        po = self.get_po(po_number, tenant_id)
        if po is None:
            return None
        lines = self.get_lines(po_number, tenant_id)
        return PurchaseOrderDetail(
            po_number=po.po_number,
            po_date=po.po_date,
            supplier_code=po.supplier_code,
            supplier_name=po.supplier_name,
            site_code=po.site_code,
            status=po.status,
            expected_date=po.expected_date,
            total_ordered_value=po.total_ordered_value,
            total_received_value=po.total_received_value,
            line_count=po.line_count,
            notes=po.notes,
            created_by=po.created_by,
            lines=lines,
        )

    def get_lines(self, po_number: str, tenant_id: int) -> list[POLineItem]:
        stmt = text("""
            SELECT
                pl.line_number, pl.drug_code, pl.ordered_quantity,
                pl.unit_price, pl.received_quantity, pl.line_total,
                ROUND(
                    pl.received_quantity / NULLIF(pl.ordered_quantity, 0), 4
                ) AS fulfillment_pct
            FROM bronze.po_lines pl
            WHERE pl.tenant_id = :tenant_id AND pl.po_number = :po_number
            ORDER BY pl.line_number
        """)
        rows = self._session.execute(
            stmt, {"tenant_id": tenant_id, "po_number": po_number}
        ).fetchall()
        return [_row_to_line(r) for r in rows]

    # ── Create ────────────────────────────────────────────────────────────

    def create_po(
        self,
        data: POCreateRequest,
        tenant_id: int,
        created_by: str | None = None,
    ) -> PurchaseOrder:
        log.info("create_po", po_date=str(data.po_date), supplier=data.supplier_code)

        # Generate PO number: PO-<tenant>-<YYYYMMDD>-<seq>
        seq_stmt = text("""
            SELECT COALESCE(MAX(
                CAST(SPLIT_PART(po_number, '-', 4) AS INT)
            ), 0) + 1
            FROM bronze.purchase_orders
            WHERE tenant_id = :tid
              AND po_number LIKE :prefix
        """)
        prefix = f"PO-{tenant_id}-{data.po_date.strftime('%Y%m%d')}-"
        seq = self._session.execute(
            seq_stmt, {"tid": tenant_id, "prefix": f"{prefix}%"}
        ).scalar_one()
        po_number = f"{prefix}{seq:04d}"

        # Insert header
        self._session.execute(
            text("""
                INSERT INTO bronze.purchase_orders
                    (tenant_id, po_number, po_date, supplier_code, site_code,
                     status, expected_date, notes, created_by, source_file)
                VALUES
                    (:tenant_id, :po_number, :po_date, :supplier_code, :site_code,
                     'draft', :expected_date, :notes, :created_by, 'api')
            """),
            {
                "tenant_id": tenant_id,
                "po_number": po_number,
                "po_date": data.po_date,
                "supplier_code": data.supplier_code,
                "site_code": data.site_code,
                "expected_date": data.expected_date,
                "notes": data.notes,
                "created_by": created_by,
            },
        )

        # Insert lines
        for idx, line in enumerate(data.lines, start=1):
            self._session.execute(
                text("""
                    INSERT INTO bronze.po_lines
                        (tenant_id, po_number, line_number, drug_code,
                         ordered_quantity, unit_price, received_quantity)
                    VALUES
                        (:tenant_id, :po_number, :line_number, :drug_code,
                         :ordered_quantity, :unit_price, 0)
                """),
                {
                    "tenant_id": tenant_id,
                    "po_number": po_number,
                    "line_number": idx,
                    "drug_code": line.drug_code,
                    "ordered_quantity": float(line.quantity),
                    "unit_price": float(line.unit_price),
                },
            )

        result = self.get_po(po_number, tenant_id)
        assert result is not None  # just inserted
        return result

    # ── Update ────────────────────────────────────────────────────────────

    def update_po(
        self,
        po_number: str,
        tenant_id: int,
        *,
        expected_date: date | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> PurchaseOrder | None:
        """Update mutable fields on a PO header."""
        sets: list[str] = []
        params: dict = {"po_number": po_number, "tenant_id": tenant_id}

        if expected_date is not None:
            sets.append("expected_date = :expected_date")
            params["expected_date"] = expected_date
        if notes is not None:
            sets.append("notes = :notes")
            params["notes"] = notes
        if status is not None:
            sets.append("status = :status")
            params["status"] = status

        if not sets:
            return self.get_po(po_number, tenant_id)

        set_clause = ", ".join(sets)
        self._session.execute(
            text(f"""
                UPDATE bronze.purchase_orders
                SET {set_clause}
                WHERE po_number = :po_number AND tenant_id = :tenant_id
            """),
            params,
        )
        return self.get_po(po_number, tenant_id)

    # ── Receive ───────────────────────────────────────────────────────────

    def receive_po_lines(
        self,
        po_number: str,
        tenant_id: int,
        lines: list[POReceiveLineRequest],
    ) -> None:
        """Update received_quantity on each line.

        Caller is responsible for:
        1. Calling this method
        2. Calling insert_stock_receipts() in the same transaction
        3. Calling recalculate_po_status() to set partial/received
        """
        for line in lines:
            self._session.execute(
                text("""
                    UPDATE bronze.po_lines
                    SET received_quantity = received_quantity + :delta
                    WHERE tenant_id = :tenant_id
                      AND po_number = :po_number
                      AND line_number = :line_number
                """),
                {
                    "tenant_id": tenant_id,
                    "po_number": po_number,
                    "line_number": line.line_number,
                    "delta": float(line.received_quantity),
                },
            )

    def insert_stock_receipts(
        self,
        po_number: str,
        tenant_id: int,
        site_code: str,
        receipt_date: date,
        lines: list[POReceiveLineRequest],
        line_details: dict[int, POCreateLineRequest],
    ) -> int:
        """Write stock receipt entries to bronze.stock_receipts.

        Returns the number of receipt rows inserted.
        """
        rows_inserted = 0
        for line in lines:
            if float(line.received_quantity) <= 0:
                continue
            detail = line_details.get(line.line_number)
            drug_code = detail.drug_code if detail else None
            unit_price = float(detail.unit_price) if detail else None

            self._session.execute(
                text("""
                    INSERT INTO bronze.stock_receipts
                        (tenant_id, source_file, receipt_date, receipt_reference,
                         drug_code, site_code, batch_number, expiry_date,
                         quantity, unit_cost, supplier_code, po_reference)
                    SELECT
                        :tenant_id, 'api:po_receive', :receipt_date, :receipt_reference,
                        :drug_code, :site_code, :batch_number, :expiry_date,
                        :quantity, :unit_cost, po.supplier_code, :po_reference
                    FROM bronze.purchase_orders po
                    WHERE po.tenant_id = :tenant_id AND po.po_number = :po_number
                """),
                {
                    "tenant_id": tenant_id,
                    "receipt_date": receipt_date,
                    "receipt_reference": po_number,
                    "drug_code": drug_code,
                    "site_code": site_code,
                    "batch_number": line.batch_number,
                    "expiry_date": line.expiry_date,
                    "quantity": float(line.received_quantity),
                    "unit_cost": unit_price,
                    "po_reference": po_number,
                    "po_number": po_number,
                },
            )
            rows_inserted += 1
        return rows_inserted

    def recalculate_po_status(self, po_number: str, tenant_id: int) -> str:
        """Recalculate and persist the PO status based on fulfilment.

        Returns the new status string.
        """
        row = self._session.execute(
            text("""
                SELECT
                    SUM(ordered_quantity)  AS total_ordered,
                    SUM(received_quantity) AS total_received
                FROM bronze.po_lines
                WHERE tenant_id = :tenant_id AND po_number = :po_number
            """),
            {"tenant_id": tenant_id, "po_number": po_number},
        ).fetchone()

        if row is None:
            return "draft"

        total_ordered = float(row._mapping["total_ordered"] or 0)
        total_received = float(row._mapping["total_received"] or 0)

        if total_received <= 0:
            new_status = "submitted"
        elif total_received >= total_ordered:
            new_status = "received"
        else:
            new_status = "partial"

        self._session.execute(
            text("""
                UPDATE bronze.purchase_orders
                SET status = :status
                WHERE tenant_id = :tenant_id AND po_number = :po_number
            """),
            {"status": new_status, "tenant_id": tenant_id, "po_number": po_number},
        )
        return new_status

    def get_line_details_map(
        self,
        po_number: str,
        tenant_id: int,
    ) -> dict[int, POCreateLineRequest]:
        """Return a dict keyed by line_number with drug_code+unit_price."""
        rows = self._session.execute(
            text("""
                SELECT line_number, drug_code, unit_price
                FROM bronze.po_lines
                WHERE tenant_id = :tenant_id AND po_number = :po_number
            """),
            {"tenant_id": tenant_id, "po_number": po_number},
        ).fetchall()
        return {
            int(r._mapping["line_number"]): POCreateLineRequest(
                drug_code=r._mapping["drug_code"],
                quantity=Decimal(str(r._mapping.get("ordered_quantity", 0))),
                unit_price=_dec(r._mapping["unit_price"]) or Decimal("0"),
            )
            for r in rows
        }

    # ── Cancel ────────────────────────────────────────────────────────────

    def cancel_po(self, po_number: str, tenant_id: int) -> PurchaseOrder | None:
        """Cancel a draft or submitted PO. Returns None if not found or not cancellable."""
        result = self._session.execute(
            text("""
                UPDATE bronze.purchase_orders
                SET status = 'cancelled'
                WHERE tenant_id = :tenant_id
                  AND po_number = :po_number
                  AND status IN ('draft', 'submitted')
                RETURNING po_number
            """),
            {"tenant_id": tenant_id, "po_number": po_number},
        ).fetchone()

        if result is None:
            return None
        return self.get_po(po_number, tenant_id)

    # ── Margin Analysis ───────────────────────────────────────────────────

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
        clauses = ["ma.tenant_id = :tenant_id"]
        params: dict = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if year is not None:
            clauses.append("ma.year = :year")
            params["year"] = year
        if month is not None:
            clauses.append("ma.month = :month")
            params["month"] = month
        if drug_code is not None:
            clauses.append("ma.drug_code = :drug_code")
            params["drug_code"] = drug_code

        where = " AND ".join(clauses)

        count_stmt = text(f"SELECT COUNT(*) FROM public_marts.agg_margin_analysis ma WHERE {where}")
        total = self._session.execute(count_stmt, params).scalar_one()

        select_stmt = text(f"""
            SELECT
                ma.drug_code, ma.drug_name, ma.drug_brand, ma.drug_category,
                ma.year, ma.month, ma.month_name,
                ma.revenue, ma.cogs, ma.gross_margin, ma.margin_pct,
                ma.units_sold
            FROM public_marts.agg_margin_analysis ma
            WHERE {where}
            ORDER BY ma.year DESC, ma.month DESC, ma.revenue DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = self._session.execute(select_stmt, params).fetchall()

        items = [
            MarginAnalysisRow(
                drug_code=r._mapping["drug_code"],
                drug_name=r._mapping.get("drug_name"),
                drug_brand=r._mapping.get("drug_brand"),
                drug_category=r._mapping.get("drug_category"),
                year=int(r._mapping["year"]),
                month=int(r._mapping["month"]),
                month_name=r._mapping.get("month_name"),
                revenue=_dec(r._mapping["revenue"]) or Decimal("0"),
                cogs=_dec(r._mapping["cogs"]) or Decimal("0"),
                gross_margin=_dec(r._mapping["gross_margin"]) or Decimal("0"),
                margin_pct=_dec(r._mapping.get("margin_pct")),
                units_sold=_dec(r._mapping.get("units_sold")),
            )
            for r in rows
        ]
        return MarginAnalysisList(
            items=items,
            total=total,
            year=year,
            month=month,
        )
