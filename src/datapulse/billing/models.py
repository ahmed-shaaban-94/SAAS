"""Pydantic models for billing API requests and responses."""

from __future__ import annotations

from datetime import datetime

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
    """Request to create a Stripe Checkout session."""

    price_id: str = Field(..., description="Stripe Price ID for the plan")
    success_url: str = Field(default="/billing?success=true")
    cancel_url: str = Field(default="/billing?canceled=true")


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
