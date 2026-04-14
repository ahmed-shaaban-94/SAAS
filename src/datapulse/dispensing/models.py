"""Pydantic models for the dispensing analytics module."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class DispenseRate(BaseModel):
    """Average quantity dispensed per day for a product at a site (last 90 days)."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    site_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    site_code: str
    site_name: str
    active_days: int
    total_dispensed_90d: JsonDecimal
    avg_daily_dispense: JsonDecimal | None
    avg_weekly_dispense: JsonDecimal | None
    avg_monthly_dispense: JsonDecimal | None
    last_dispense_date_key: int | None = None


class DaysOfStock(BaseModel):
    """Days of stock remaining per product per site."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    site_key: int
    drug_code: str
    drug_name: str
    site_code: str
    site_name: str
    current_quantity: JsonDecimal
    avg_daily_dispense: JsonDecimal | None
    days_of_stock: JsonDecimal | None  # None if no dispense history
    avg_weekly_dispense: JsonDecimal | None
    avg_monthly_dispense: JsonDecimal | None
    last_dispense_date_key: int | None = None


class VelocityClassification(BaseModel):
    """Product velocity classification (fast/normal/slow/dead) relative to category average."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    drug_category: str | None
    lifecycle_phase: str | None  # from feat_product_lifecycle
    velocity_class: str  # fast_mover | normal_mover | slow_mover | dead_stock
    avg_daily_dispense: JsonDecimal | None
    category_avg_daily: JsonDecimal | None


class StockoutRisk(BaseModel):
    """Product at risk of stockout with risk level and suggested reorder quantity."""

    model_config = ConfigDict(frozen=True)

    product_key: int
    site_key: int
    drug_code: str
    drug_name: str
    site_code: str
    site_name: str
    current_quantity: JsonDecimal
    days_of_stock: JsonDecimal | None
    avg_daily_dispense: JsonDecimal | None
    reorder_point: Decimal
    reorder_lead_days: int
    min_stock: Decimal
    risk_level: str  # stockout | critical | at_risk | safe
    suggested_reorder_qty: JsonDecimal


class DispensingFilter(BaseModel):
    """Common query filters for dispensing analytics endpoints."""

    model_config = ConfigDict(frozen=True)

    site_key: int | None = None
    drug_code: Annotated[str | None, Field(max_length=100)] = None
    velocity_class: Annotated[str | None, Field(max_length=50)] = None
    risk_level: Annotated[str | None, Field(max_length=50)] = None
    limit: int = Field(default=100, ge=1, le=500)
