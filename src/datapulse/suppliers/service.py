"""Business logic layer for suppliers."""

from __future__ import annotations

import structlog
from fastapi import HTTPException

from datapulse.suppliers.models import (
    SupplierCreateRequest,
    SupplierInfo,
    SupplierList,
    SupplierPerformance,
    SupplierUpdateRequest,
)
from datapulse.suppliers.repository import SuppliersRepository

log = structlog.get_logger(__name__)


class SuppliersService:
    """Business logic for supplier directory management."""

    def __init__(self, repo: SuppliersRepository) -> None:
        self._repo = repo

    def list_suppliers(
        self,
        *,
        tenant_id: int,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SupplierList:
        return self._repo.list_suppliers(
            tenant_id=tenant_id,
            is_active=is_active,
            offset=offset,
            limit=limit,
        )

    def get_supplier(self, supplier_code: str, tenant_id: int) -> SupplierInfo:
        supplier = self._repo.get_supplier(supplier_code, tenant_id)
        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier '{supplier_code}' not found",
            )
        return supplier

    def create_supplier(
        self,
        data: SupplierCreateRequest,
        tenant_id: int,
    ) -> SupplierInfo:
        # Check for duplicate
        existing = self._repo.get_supplier(data.supplier_code, tenant_id)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Supplier with code '{data.supplier_code}' already exists",
            )
        return self._repo.create_supplier(data, tenant_id)

    def update_supplier(
        self,
        supplier_code: str,
        tenant_id: int,
        data: SupplierUpdateRequest,
    ) -> SupplierInfo:
        result = self._repo.update_supplier(supplier_code, tenant_id, data)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier '{supplier_code}' not found",
            )
        return result

    def get_performance(
        self,
        supplier_code: str,
        tenant_id: int,
    ) -> SupplierPerformance:
        # Ensure supplier exists
        supplier = self._repo.get_supplier(supplier_code, tenant_id)
        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier '{supplier_code}' not found",
            )

        perf = self._repo.get_supplier_performance(supplier_code, tenant_id)
        if perf is None:
            # Supplier exists but no orders yet — return zero-value performance
            return SupplierPerformance(
                supplier_code=supplier.supplier_code,
                supplier_name=supplier.supplier_name,
                contracted_lead_days=supplier.lead_time_days,
                total_orders=0,
                completed_orders=0,
                cancelled_orders=0,
                avg_lead_days=None,
                fill_rate=0,  # type: ignore[arg-type]
                total_spend=0,  # type: ignore[arg-type]
                total_received=0,  # type: ignore[arg-type]
                cancellation_rate=None,
            )
        return perf
