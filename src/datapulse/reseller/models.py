"""Pydantic models for reseller management."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class ResellerCreate(BaseModel):
    """Input model for creating a reseller."""

    name: str
    contact_email: str
    contact_name: str | None = None
    commission_pct: JsonDecimal = Field(default=Decimal("20.00"))


class ResellerResponse(BaseModel):
    """A reseller partner."""

    model_config = ConfigDict(frozen=True)

    reseller_id: int
    name: str
    contact_email: str
    contact_name: str | None = None
    commission_pct: JsonDecimal
    stripe_connect_id: str | None = None
    is_active: bool = True
    tenant_count: int = 0
    created_at: datetime
    updated_at: datetime


class ResellerTenantResponse(BaseModel):
    """A tenant managed by a reseller."""

    model_config = ConfigDict(frozen=True)

    tenant_id: int
    tenant_name: str
    plan: str
    created_at: datetime | None = None


class CommissionResponse(BaseModel):
    """A commission record for a reseller."""

    model_config = ConfigDict(frozen=True)

    id: int
    reseller_id: int
    tenant_id: int
    tenant_name: str = ""
    period: str
    mrr_amount: JsonDecimal
    commission_amount: JsonDecimal
    commission_pct: JsonDecimal
    status: str


class PayoutResponse(BaseModel):
    """A payout record for a reseller."""

    model_config = ConfigDict(frozen=True)

    id: int
    reseller_id: int
    amount: JsonDecimal
    currency: str = "USD"
    stripe_transfer_id: str | None = None
    status: str
    period_from: str
    period_to: str
    created_at: datetime


class ResellerDashboard(BaseModel):
    """Reseller dashboard overview."""

    model_config = ConfigDict(frozen=True)

    reseller: ResellerResponse
    tenants: list[ResellerTenantResponse] = Field(default_factory=list)
    total_mrr: JsonDecimal = Field(default=Decimal("0"))
    total_commissions: JsonDecimal = Field(default=Decimal("0"))
    pending_payout: JsonDecimal = Field(default=Decimal("0"))
