"""Delivery dispatch + rider routing models for POS v9 Phase C (issue #628)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class RiderStatus(StrEnum):
    available = "available"
    busy = "busy"
    offline = "offline"


class DeliveryStatus(StrEnum):
    pending = "pending"
    dispatched = "dispatched"
    delivered = "delivered"
    failed = "failed"


class DeliveryChannel(StrEnum):
    in_store = "in_store"
    phone = "phone"
    app = "app"


# ─── Rider models ─────────────────────────────────────────────────────────────


class RiderResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    name: str
    phone: str
    status: RiderStatus
    current_terminal_id: int | None = None
    created_at: datetime
    updated_at: datetime


class AvailableRidersResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    riders: list[RiderResponse]
    total: int


# ─── Delivery models ──────────────────────────────────────────────────────────


class CreateDeliveryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: int = Field(ge=1)
    address: str = Field(min_length=1, max_length=500)
    landmark: str | None = Field(default=None, max_length=300)
    channel: DeliveryChannel = DeliveryChannel.phone
    assigned_rider_id: int | None = Field(default=None, ge=1)
    delivery_fee: JsonDecimal = Field(default=Decimal("0"), ge=0)
    eta_minutes: int | None = Field(default=None, ge=1, le=480)
    notes: str | None = Field(default=None, max_length=500)


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    transaction_id: int
    address: str
    landmark: str | None = None
    channel: DeliveryChannel
    assigned_rider_id: int | None = None
    rider: RiderResponse | None = None
    delivery_fee: JsonDecimal
    eta_minutes: int | None = None
    status: DeliveryStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
