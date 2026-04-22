"""Pydantic models for billing API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BillingStatus(BaseModel):
    """Current billing status for a tenant."""

    plan: str = "starter"
    plan_name: str = "Starter"
    price_display: str = "$0/mo"
    subscription_status: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    # Usage
    data_sources_used: int = 0
    data_sources_limit: int = 1
    total_rows_used: int = 0
    total_rows_limit: int = 10_000
    # Feature flags
    ai_insights: bool = False
    pipeline_automation: bool = False
    quality_gates: bool = False


class CheckoutRequest(BaseModel):
    """Request to create a Checkout session.

    For Stripe (USD): ``price_id`` is the Stripe Price ID.
    For Paymob/InstaPay (EGP): ``price_id`` is the plan key (e.g. ``"pro"``).
    Set ``currency="EGP"`` to route to the Egyptian payment provider.
    """

    price_id: str = Field(..., description="Stripe Price ID (USD) or plan key (EGP)")
    success_url: str = Field(default="/billing?success=true")
    cancel_url: str = Field(default="/billing?canceled=true")
    currency: Literal["USD", "EGP"] = Field(
        default="USD",
        description="ISO-4217 currency code — determines the payment provider",
    )


class InstapayUploadRequest(BaseModel):
    """Tenant uploads proof of payment for InstaPay manual reconciliation."""

    plan: str = Field(..., description="Plan key the tenant is subscribing to")
    amount_egp: int = Field(..., ge=1, description="Amount transferred in EGP")
    transfer_reference: str = Field(..., min_length=4, description="Bank transfer reference")
    proof_url: str = Field(..., description="Public URL of the uploaded payment screenshot")


class InstapayApproveRequest(BaseModel):
    """Admin approves an InstaPay transfer and activates the subscription."""

    tenant_id: int = Field(..., ge=1)
    plan: str = Field(..., description="Plan to activate")
    admin_note: str = Field(default="", description="Optional audit note")


class CheckoutResponse(BaseModel):
    """Response with the Stripe Checkout session URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with the Stripe Customer Portal URL."""

    portal_url: str


class WebhookResult(BaseModel):
    """Internal result of processing a webhook event."""

    event_type: str
    tenant_id: int | None = None
    plan: str | None = None
    status: str = "processed"
