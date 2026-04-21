"""Product search, stock info, catalog pull, and receipt-email models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class BatchSummary(BaseModel):
    """Summary of a single drug batch at the POS."""

    model_config = ConfigDict(frozen=True)

    batch_number: str
    expiry_date: date | None = None
    quantity_available: JsonDecimal


class PosProductResult(BaseModel):
    """Search result for a drug at the POS terminal."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    drug_brand: str | None = None
    drug_cluster: str | None = None
    unit_price: JsonDecimal
    stock_quantity: JsonDecimal
    is_controlled: bool = False
    requires_pharmacist: bool = False


class PosStockInfo(BaseModel):
    """Stock and batch information for a specific drug at a site."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    site_code: str
    quantity_available: JsonDecimal
    batches: list[BatchSummary] = Field(default_factory=list)


class EmailReceiptRequest(BaseModel):
    """Request body to email a receipt to a customer."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CatalogProductEntry(BaseModel):
    """One product entry in the offline-catalog pull response."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    drug_brand: str | None = None
    drug_cluster: str | None = None
    drug_category: str | None = None
    is_controlled: bool
    requires_pharmacist: bool
    unit_price: JsonDecimal
    updated_at: str  # ISO timestamp (server wall-clock, not dim_product field)


class CatalogProductPage(BaseModel):
    """Cursor-paginated catalog product response (M3b pull-sync)."""

    model_config = ConfigDict(frozen=True)

    items: list[CatalogProductEntry]
    next_cursor: str | None  # last drug_code in page, or None when exhausted


class CatalogStockEntry(BaseModel):
    """One batch-level stock entry in the offline-catalog pull response."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    site_code: str
    batch_number: str
    quantity: JsonDecimal
    expiry_date: date | None = None
    updated_at: str  # loaded_at ISO timestamp used as cursor


class CatalogStockPage(BaseModel):
    """Cursor-paginated catalog stock response (M3b pull-sync)."""

    model_config = ConfigDict(frozen=True)

    items: list[CatalogStockEntry]
    next_cursor: str | None  # last loaded_at ISO, or None when exhausted
