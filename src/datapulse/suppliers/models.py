"""Pydantic models for the Suppliers module.

All models are frozen (immutable) to prevent accidental mutation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datapulse.types import JsonDecimal


class SupplierInfo(BaseModel):
    """Supplier directory entry."""

    model_config = ConfigDict(frozen=True)

    supplier_code: str
    supplier_name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    payment_terms_days: int = 30
    lead_time_days: int = 7
    is_active: bool = True
    notes: str | None = None


class SupplierPerformance(BaseModel):
    """Supplier performance metrics from agg_supplier_performance."""

    model_config = ConfigDict(frozen=True)

    supplier_code: str
    supplier_name: str
    contracted_lead_days: int | None = None
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    avg_lead_days: JsonDecimal | None = None
    fill_rate: JsonDecimal
    total_spend: JsonDecimal
    total_received: JsonDecimal
    cancellation_rate: JsonDecimal | None = None


class SupplierCreateRequest(BaseModel):
    """Request body for creating a new supplier."""

    model_config = ConfigDict(frozen=True)

    supplier_code: str
    supplier_name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    payment_terms_days: int = Field(default=30, ge=0)
    lead_time_days: int = Field(default=7, ge=0)
    is_active: bool = True
    notes: str | None = None

    @field_validator("supplier_code", "supplier_name")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Must not be empty")
        return v


class SupplierUpdateRequest(BaseModel):
    """Request body for partially updating a supplier."""

    model_config = ConfigDict(frozen=True)

    supplier_name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    notes: str | None = None


class SupplierList(BaseModel):
    """Paginated list of suppliers."""

    model_config = ConfigDict(frozen=True)

    items: list[SupplierInfo]
    total: int
    offset: int
    limit: int
