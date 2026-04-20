"""Pydantic models for the expiry module."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class BatchInfo(BaseModel):
    """Batch dimension row with computed expiry status."""

    model_config = ConfigDict(frozen=True)

    batch_key: int
    drug_code: str
    drug_name: str
    site_code: str
    batch_number: str
    expiry_date: date
    current_quantity: JsonDecimal
    days_to_expiry: int
    alert_level: str  # expired|critical|warning|caution|safe
    computed_status: str  # active|near_expiry|expired|quarantined|written_off


class ExpiryAlert(BaseModel):
    """A batch approaching or past its expiry date."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    drug_brand: str | None = None
    batch_number: str
    site_code: str
    expiry_date: date
    current_quantity: JsonDecimal
    days_to_expiry: int
    alert_level: str  # expired|critical|warning|caution|safe


class ExpirySummary(BaseModel):
    """Expiry counts aggregated per site."""

    model_config = ConfigDict(frozen=True)

    site_key: int
    site_code: str
    site_name: str
    expiry_bucket: str
    batch_count: int
    total_quantity: JsonDecimal
    total_value: JsonDecimal


class ExpiryExposureTier(BaseModel):
    """Tenant-aggregate expiry exposure for a single 30/60/90-day tier.

    Powers the three-card tier widget on the new dashboard design (#506).
    The response always contains exactly three rows — zero-valued tiers
    included — so the frontend can render the fixed layout without
    conditional logic.
    """

    model_config = ConfigDict(frozen=True)

    tier: str  # "30d" | "60d" | "90d"
    label: str  # "Within 30 days" | "31-60 days" | "61-90 days"
    total_egp: JsonDecimal
    batch_count: int
    tone: str  # "red" | "amber" | "green"


class ExpiryCalendarDay(BaseModel):
    """Day-by-day expiry count for the calendar view."""

    model_config = ConfigDict(frozen=True)

    expiry_date: date
    batch_count: int
    total_quantity: JsonDecimal
    alert_level: str  # expired|critical|warning|caution|safe


class ExpiryFilter(BaseModel):
    """Common query filters for expiry endpoints."""

    model_config = ConfigDict(frozen=True)

    site_code: Annotated[str | None, Field(max_length=100)] = None
    drug_code: Annotated[str | None, Field(max_length=100)] = None
    alert_level: Annotated[str | None, Field(max_length=50)] = None
    days_threshold: int = Field(default=90, ge=1, le=365)
    limit: int = Field(default=100, ge=1, le=500)


class QuarantineRequest(BaseModel):
    """Request body for quarantining a batch."""

    model_config = ConfigDict(frozen=True)

    drug_code: Annotated[str, Field(max_length=100)]
    site_code: Annotated[str, Field(max_length=100)]
    batch_number: Annotated[str, Field(max_length=100)]
    reason: Annotated[str, Field(max_length=500)]


class WriteOffRequest(BaseModel):
    """Request body for writing off a batch."""

    model_config = ConfigDict(frozen=True)

    drug_code: Annotated[str, Field(max_length=100)]
    site_code: Annotated[str, Field(max_length=100)]
    batch_number: Annotated[str, Field(max_length=100)]
    reason: Annotated[str, Field(max_length=500)]
    quantity: JsonDecimal


class FefoRequest(BaseModel):
    """Request body for FEFO batch selection."""

    model_config = ConfigDict(frozen=True)

    drug_code: Annotated[str, Field(max_length=100)]
    site_code: Annotated[str, Field(max_length=100)]
    required_quantity: JsonDecimal


class FefoResponse(BaseModel):
    """Result of FEFO batch selection."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    site_code: str
    required_quantity: JsonDecimal
    fulfilled: bool
    remaining_unfulfilled: JsonDecimal
    selections: list[dict]
