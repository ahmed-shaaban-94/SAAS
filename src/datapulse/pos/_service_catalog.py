"""Catalog, stock lookup, and receipt-regeneration mixin for :class:`PosService`.

Owns read-only product/stock access surface plus the idempotent re-generation
of stored receipts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos._service_helpers import is_controlled, to_decimal
from datapulse.pos.models import (
    BatchSummary,
    CatalogProductEntry,
    CatalogProductPage,
    CatalogStockEntry,
    CatalogStockPage,
    PosProductResult,
    PosStockInfo,
)
from datapulse.pos.models.clinical import (
    AlternativeItem,
    CrossSellItem,
    DrugDetail,
)
from datapulse.pos.receipt import generate_pdf_receipt, generate_thermal_receipt

if TYPE_CHECKING:
    from datapulse.pos.inventory_contract import InventoryServiceProtocol
    from datapulse.pos.repository import PosRepository

log = get_logger(__name__)


class CatalogMixin:
    """Mixin providing product search, catalog sync, stock lookups, and receipts.

    Requires ``self._repo`` and ``self._inventory`` to be set by
    :meth:`PosService.__init__`.
    """

    _repo: PosRepository
    _inventory: InventoryServiceProtocol

    def search_products(
        self,
        query: str,
        *,
        site_code: str | None = None,
        limit: int = 20,
    ) -> list[PosProductResult]:
        """Search the product catalog. ``site_code`` reserved for future per-site stock joins.

        Stock quantity is left at 0 here; callers that need live stock should
        call :meth:`get_stock_info` for the selected drug.
        """
        _ = site_code  # reserved
        rows = self._repo.search_dim_products(query, limit=limit)
        results: list[PosProductResult] = []
        for r in rows:
            results.append(
                PosProductResult(
                    drug_code=r["drug_code"],
                    drug_name=r["drug_name"],
                    drug_brand=r.get("drug_brand"),
                    drug_cluster=r.get("drug_cluster"),
                    unit_price=to_decimal(r.get("unit_price", 0)),
                    stock_quantity=Decimal("0"),
                    is_controlled=is_controlled(r.get("drug_category")),
                    requires_pharmacist=is_controlled(r.get("drug_category")),
                ),
            )
        return results

    def get_catalog_products(
        self,
        cursor: str | None,
        limit: int,
    ) -> CatalogProductPage:
        """Return a paginated slice of the full product catalog for offline sync.

        *cursor* is the last ``drug_code`` received; pass ``None`` for the first
        page.  When the returned ``next_cursor`` is ``None`` the catalog is
        exhausted and the desktop should reset to cursor=None on the next cycle.
        """
        rows = self._repo.list_catalog_products(cursor=cursor, limit=limit)
        now_iso = datetime.now(tz=UTC).replace(microsecond=0).isoformat()
        items = [
            CatalogProductEntry(
                drug_code=r["drug_code"],
                drug_name=r["drug_name"],
                drug_brand=r.get("drug_brand"),
                drug_cluster=r.get("drug_cluster"),
                drug_category=r.get("drug_category"),
                is_controlled=is_controlled(r.get("drug_category")),
                requires_pharmacist=is_controlled(r.get("drug_category")),
                unit_price=to_decimal(r.get("unit_price", 0)),
                updated_at=now_iso,
            )
            for r in rows
        ]
        next_cursor = items[-1].drug_code if len(items) == limit else None
        return CatalogProductPage(items=items, next_cursor=next_cursor)

    def get_catalog_stock(
        self,
        site: str | None,
        cursor: str | None,
        limit: int,
    ) -> CatalogStockPage:
        """Return a paginated slice of active batches from stg_batches for offline sync.

        *cursor* is the last ``loaded_at`` ISO timestamp received; pass ``None``
        for the first page.  When the returned ``next_cursor`` is ``None`` all
        active batches have been delivered for this cycle.
        """
        rows = self._repo.list_catalog_stock(site=site, cursor=cursor, limit=limit)
        items = [
            CatalogStockEntry(
                drug_code=r["drug_code"],
                site_code=r["site_code"],
                batch_number=r["batch_number"],
                quantity=to_decimal(r.get("current_quantity", 0)),
                expiry_date=r.get("expiry_date"),
                updated_at=(
                    r["loaded_at"].isoformat()
                    if hasattr(r["loaded_at"], "isoformat")
                    else str(r["loaded_at"])
                ),
            )
            for r in rows
        ]
        next_cursor = items[-1].updated_at if len(items) == limit else None
        return CatalogStockPage(items=items, next_cursor=next_cursor)

    def get_drug_detail(self, drug_code: str) -> DrugDetail | None:
        """Return drug detail + POS-owned clinical metadata (#623).

        ``None`` when the drug_code is unknown in ``dim_product``; the route
        layer converts that to a 404.
        """
        row = self._repo.get_drug_detail(drug_code)
        if row is None:
            return None
        return DrugDetail(
            drug_code=row["drug_code"],
            drug_name=row["drug_name"],
            drug_brand=row.get("drug_brand"),
            drug_cluster=row.get("drug_cluster"),
            drug_category=row.get("drug_category"),
            unit_price=to_decimal(row.get("unit_price", 0)),
            counseling_text=row.get("counseling_text"),
            active_ingredient=row.get("active_ingredient"),
        )

    def get_cross_sell(self, drug_code: str) -> list[CrossSellItem]:
        """Return the static cross-sell suggestions for ``drug_code`` (#623).

        Returns an empty list — never raises — when the drug has no rules;
        the clinical panel card hides client-side.
        """
        rows = self._repo.get_cross_sell_rules(drug_code)
        return [
            CrossSellItem(
                drug_code=r["drug_code"],
                drug_name=r["drug_name"],
                reason=r["reason"],
                reason_tag=r["reason_tag"],
                unit_price=to_decimal(r.get("unit_price", 0)),
            )
            for r in rows
        ]

    def get_alternatives(self, drug_code: str) -> list[AlternativeItem]:
        """Return generic alternatives with positive savings (#623).

        Filters out siblings where ``savings_egp <= 0`` so the UI only
        surfaces true cost-savers. Drugs with no ``active_ingredient`` on
        file return an empty list (repo query is a no-op in that case).
        """
        rows = self._repo.get_alternatives_by_ingredient(drug_code)
        items: list[AlternativeItem] = []
        for r in rows:
            primary_price = to_decimal(r.get("primary_unit_price", 0))
            alt_price = to_decimal(r.get("unit_price", 0))
            savings = primary_price - alt_price
            if savings <= 0:
                continue
            items.append(
                AlternativeItem(
                    drug_code=r["drug_code"],
                    drug_name=r["drug_name"],
                    unit_price=alt_price,
                    savings_egp=savings,
                )
            )
        return items

    async def get_stock_info(
        self,
        drug_code: str,
        site_code: str,
    ) -> PosStockInfo:
        """Return live stock + per-batch info for a single drug at a site."""
        stock = await self._inventory.get_stock_level(drug_code, site_code)
        batches = await self._inventory.check_batch_expiry(drug_code, site_code)
        return PosStockInfo(
            drug_code=drug_code,
            site_code=site_code,
            quantity_available=stock.quantity_available,
            batches=[
                BatchSummary(
                    batch_number=b.batch_number,
                    expiry_date=b.expiry_date,
                    quantity_available=b.quantity_available,
                )
                for b in batches
            ],
        )

    def get_receipt_pdf(self, transaction_id: int, tenant_id: int) -> bytes:
        """Return stored PDF receipt bytes; regenerate on demand if missing."""
        row = self._repo.get_receipt(transaction_id, "pdf")
        if row and row.get("content"):
            return bytes(row["content"])
        return self._regenerate_receipt(transaction_id, tenant_id, "pdf")

    def get_receipt_thermal(self, transaction_id: int, tenant_id: int) -> bytes:
        """Return stored thermal ESC/POS bytes; regenerate on demand if missing."""
        row = self._repo.get_receipt(transaction_id, "thermal")
        if row and row.get("content"):
            return bytes(row["content"])
        return self._regenerate_receipt(transaction_id, tenant_id, "thermal")

    def _regenerate_receipt(self, transaction_id: int, tenant_id: int, fmt: str) -> bytes:
        """Regenerate a receipt on demand (fallback when no stored receipt exists)."""
        from fastapi import HTTPException  # local import avoids circular dependency

        header = self._repo.get_transaction(transaction_id)
        if header is None:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        items = self._repo.get_transaction_items(transaction_id)
        payment_info = {
            "method": header.get("payment_method", "cash"),
            "amount_charged": to_decimal(header.get("grand_total", 0)),
            "change_due": Decimal("0"),
            "insurance_no": None,
        }
        content = (
            generate_pdf_receipt(header, items, payment_info)
            if fmt == "pdf"
            else generate_thermal_receipt(header, items, payment_info)
        )
        self._repo.save_receipt(
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            fmt=fmt,
            content=content,
        )
        return content
