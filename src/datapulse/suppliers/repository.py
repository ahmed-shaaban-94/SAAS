"""Data-access layer for the suppliers module.

All SQL uses parameterized queries via SQLAlchemy text() — no f-string
interpolation of user-supplied values.
"""

from __future__ import annotations

from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.suppliers.models import (
    SupplierCreateRequest,
    SupplierInfo,
    SupplierList,
    SupplierPerformance,
    SupplierUpdateRequest,
)

log = structlog.get_logger(__name__)


def _dec(v) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(v))


def _row_to_supplier(row) -> SupplierInfo:
    m = row._mapping
    return SupplierInfo(
        supplier_code=m["supplier_code"],
        supplier_name=m["supplier_name"],
        contact_name=m.get("contact_name"),
        contact_phone=m.get("contact_phone"),
        contact_email=m.get("contact_email"),
        address=m.get("address"),
        payment_terms_days=int(m.get("payment_terms_days") or 30),
        lead_time_days=int(m.get("lead_time_days") or 7),
        is_active=bool(m.get("is_active", True)),
        notes=m.get("notes"),
    )


class SuppliersRepository:
    """Thin data-access layer for supplier directory operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── List / Read ───────────────────────────────────────────────────────

    def list_suppliers(
        self,
        *,
        tenant_id: int,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SupplierList:
        clauses = ["tenant_id = :tenant_id"]
        params: dict = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if is_active is not None:
            clauses.append("is_active = :is_active")
            params["is_active"] = is_active

        where = " AND ".join(clauses)

        total = self._session.execute(
            text(f"SELECT COUNT(*) FROM bronze.suppliers WHERE {where}"),
            params,
        ).scalar_one()

        rows = self._session.execute(
            text(f"""
                SELECT
                    supplier_code, supplier_name, contact_name, contact_phone,
                    contact_email, address, payment_terms_days, lead_time_days,
                    is_active, notes
                FROM bronze.suppliers
                WHERE {where}
                ORDER BY supplier_name
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()

        return SupplierList(
            items=[_row_to_supplier(r) for r in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_supplier(self, supplier_code: str, tenant_id: int) -> SupplierInfo | None:
        row = self._session.execute(
            text("""
                SELECT
                    supplier_code, supplier_name, contact_name, contact_phone,
                    contact_email, address, payment_terms_days, lead_time_days,
                    is_active, notes
                FROM bronze.suppliers
                WHERE tenant_id = :tenant_id AND supplier_code = :supplier_code
                LIMIT 1
            """),
            {"tenant_id": tenant_id, "supplier_code": supplier_code},
        ).fetchone()
        return _row_to_supplier(row) if row else None

    # ── Create / Update ───────────────────────────────────────────────────

    def create_supplier(
        self,
        data: SupplierCreateRequest,
        tenant_id: int,
    ) -> SupplierInfo:
        log.info("create_supplier", code=data.supplier_code, tenant=tenant_id)
        self._session.execute(
            text("""
                INSERT INTO bronze.suppliers
                    (tenant_id, supplier_code, supplier_name, contact_name,
                     contact_phone, contact_email, address, payment_terms_days,
                     lead_time_days, is_active, notes, source_file)
                VALUES
                    (:tenant_id, :supplier_code, :supplier_name, :contact_name,
                     :contact_phone, :contact_email, :address, :payment_terms_days,
                     :lead_time_days, :is_active, :notes, 'api')
                ON CONFLICT (tenant_id, supplier_code) DO NOTHING
            """),
            {
                "tenant_id": tenant_id,
                "supplier_code": data.supplier_code,
                "supplier_name": data.supplier_name,
                "contact_name": data.contact_name,
                "contact_phone": data.contact_phone,
                "contact_email": data.contact_email,
                "address": data.address,
                "payment_terms_days": data.payment_terms_days,
                "lead_time_days": data.lead_time_days,
                "is_active": data.is_active,
                "notes": data.notes,
            },
        )
        result = self.get_supplier(data.supplier_code, tenant_id)
        assert result is not None
        return result

    def update_supplier(
        self,
        supplier_code: str,
        tenant_id: int,
        data: SupplierUpdateRequest,
    ) -> SupplierInfo | None:
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return self.get_supplier(supplier_code, tenant_id)

        _updatable = frozenset(
            {
                "supplier_name",
                "contact_name",
                "contact_phone",
                "contact_email",
                "address",
                "payment_terms_days",
                "lead_time_days",
                "is_active",
                "notes",
            }
        )

        sets: list[str] = []
        params: dict = {"supplier_code": supplier_code, "tenant_id": tenant_id}
        for key, value in fields.items():
            if key not in _updatable:
                continue
            sets.append(f"{key} = :{key}")
            params[key] = value

        if not sets:
            return self.get_supplier(supplier_code, tenant_id)

        set_clause = ", ".join(sets)
        result = self._session.execute(
            text(f"""
                UPDATE bronze.suppliers
                SET {set_clause}
                WHERE tenant_id = :tenant_id AND supplier_code = :supplier_code
                RETURNING supplier_code
            """),
            params,
        ).fetchone()

        if result is None:
            return None
        return self.get_supplier(supplier_code, tenant_id)

    # ── Performance ───────────────────────────────────────────────────────

    def get_supplier_performance(
        self,
        supplier_code: str,
        tenant_id: int,
    ) -> SupplierPerformance | None:
        row = self._session.execute(
            text("""
                SELECT
                    sp.supplier_code,
                    sp.supplier_name,
                    sp.contracted_lead_days,
                    sp.total_orders,
                    sp.completed_orders,
                    sp.cancelled_orders,
                    sp.avg_lead_days,
                    sp.fill_rate,
                    sp.total_spend,
                    sp.total_received,
                    sp.cancellation_rate
                FROM public_marts.agg_supplier_performance sp
                WHERE sp.tenant_id = :tenant_id
                  AND sp.supplier_code = :supplier_code
                LIMIT 1
            """),
            {"tenant_id": tenant_id, "supplier_code": supplier_code},
        ).fetchone()

        if row is None:
            return None
        m = row._mapping
        return SupplierPerformance(
            supplier_code=m["supplier_code"],
            supplier_name=m["supplier_name"],
            contracted_lead_days=m.get("contracted_lead_days"),
            total_orders=int(m.get("total_orders") or 0),
            completed_orders=int(m.get("completed_orders") or 0),
            cancelled_orders=int(m.get("cancelled_orders") or 0),
            avg_lead_days=_dec(m.get("avg_lead_days")),
            fill_rate=_dec(m.get("fill_rate")) or Decimal("0"),
            total_spend=_dec(m.get("total_spend")) or Decimal("0"),
            total_received=_dec(m.get("total_received")) or Decimal("0"),
            cancellation_rate=_dec(m.get("cancellation_rate")),
        )
