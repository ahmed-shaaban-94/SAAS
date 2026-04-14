"""Pydantic models for the inventory module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class StockLevel(BaseModel):
    """Current stock level for a product at a site."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    site_key: int
    site_code: str
    site_name: str
    current_quantity: JsonDecimal
    total_received: JsonDecimal
    total_dispensed: JsonDecimal
    total_wastage: JsonDecimal
    last_movement_date: date | None = None


class StockMovement(BaseModel):
    """A single movement event from the stock movements fact table."""

    model_config = ConfigDict(frozen=True)

    movement_key: int
    movement_date: date
    movement_type: str
    drug_code: str
    drug_name: str
    site_code: str
    batch_number: str | None = None
    quantity: JsonDecimal
    unit_cost: JsonDecimal | None = None
    reference: str | None = None


class StockValuation(BaseModel):
    """Stock valuation (weighted average cost) for a product at a site."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_code: str
    drug_name: str
    site_key: int
    site_code: str
    weighted_avg_cost: JsonDecimal
    current_quantity: JsonDecimal
    stock_value: JsonDecimal


class InventoryCount(BaseModel):
    """A physical inventory count record."""

    model_config = ConfigDict(frozen=True)

    count_key: int
    tenant_id: int
    product_key: int
    site_key: int
    count_date: date
    drug_code: str | None = None
    site_code: str | None = None
    batch_number: str | None = None
    counted_quantity: JsonDecimal
    counted_by: str | None = None


class StockReconciliation(BaseModel):
    """Reconciliation between physical count and calculated stock level."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    site_key: int
    count_date: date
    drug_code: str
    drug_name: str
    site_code: str
    site_name: str
    counted_quantity: JsonDecimal
    calculated_quantity: JsonDecimal
    variance: JsonDecimal
    variance_pct: JsonDecimal | None = None


class ReorderAlert(BaseModel):
    """A product/site that has fallen at or below its reorder point."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    site_key: int
    drug_code: str
    drug_name: str
    site_code: str
    current_quantity: JsonDecimal
    reorder_point: Decimal
    reorder_quantity: Decimal


class InventoryFilter(BaseModel):
    """Common query filters for inventory endpoints."""

    model_config = ConfigDict(frozen=True)

    site_key: int | None = None
    drug_code: Annotated[str | None, Field(max_length=100)] = None
    movement_type: Annotated[str | None, Field(max_length=50)] = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(default=50, ge=1, le=500)


class AdjustmentRequest(BaseModel):
    """Request body for creating a manual stock adjustment."""

    model_config = ConfigDict(frozen=True)

    drug_code: Annotated[str, Field(max_length=100)]
    site_code: Annotated[str, Field(max_length=100)]
    adjustment_type: Annotated[str, Field(max_length=50)]
    quantity: JsonDecimal
    batch_number: Annotated[str | None, Field(max_length=100)] = None
    reason: Annotated[str, Field(max_length=500)]


class ReorderConfigFilter(BaseModel):
    """Query filters for reorder config list endpoint."""

    model_config = ConfigDict(frozen=True)

    site_code: Annotated[str | None, Field(max_length=100)] = None
    drug_code: Annotated[str | None, Field(max_length=100)] = None
    is_active: bool | None = True
    limit: int = Field(default=100, ge=1, le=500)
