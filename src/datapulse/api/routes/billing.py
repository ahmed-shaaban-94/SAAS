"""Billing API endpoints — Stripe checkout, portal, webhook, and status."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import text

from datapulse.api.deps import CurrentUser, get_billing_service
from datapulse.api.limiter import limiter
from datapulse.billing.models import (
    BillingStatus,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
)
from datapulse.billing.service import BillingService

logger = structlog.get_logger()

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/status", response_model=BillingStatus)
def get_billing_status(
    user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> BillingStatus:
    """Return the current tenant's billing status, plan, and usage."""
    tenant_id = int(user.get("tenant_id", "1"))
    return service.get_billing_status(tenant_id)


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> CheckoutResponse:
    """Create a Stripe Checkout session for plan upgrade."""
    tenant_id = int(user.get("tenant_id", "1"))
    email = user.get("email", "")
    tenant_name = str(user.get("name", f"Tenant {tenant_id}"))

    try:
        return service.create_checkout_session(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            email=email,
            price_id=body.price_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> PortalResponse:
    """Create a Stripe Customer Portal session for subscription management."""
    tenant_id = int(user.get("tenant_id", "1"))

    try:
        return service.create_portal_session(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/webhook", include_in_schema=False)
@limiter.limit("60/minute")
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
) -> dict:
    """Handle Stripe webhook events. Not behind JWT — uses Stripe signature verification."""
    from datapulse.billing.repository import BillingRepository
    from datapulse.billing.service import BillingService
    from datapulse.billing.stripe_client import StripeClient
    from datapulse.config import get_settings
    from datapulse.core.db import get_session_factory

    settings = get_settings()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    payload = await request.body()

    session = get_session_factory()()
    try:
        # Webhook uses raw session (no tenant RLS — it resolves tenant from Stripe customer)
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        repo = BillingRepository(session)
        client = StripeClient(settings.stripe_secret_key)
        service = BillingService(
            repo,
            client,
            price_to_plan=settings.stripe_price_to_plan_map,
            base_url=settings.billing_base_url,
        )

        result = service.handle_webhook_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
        session.commit()
        return {"status": result.status, "event_type": result.event_type}
    except Exception as e:
        session.rollback()
        logger.error("webhook_error", error=str(e))
        raise HTTPException(status_code=400, detail="Webhook processing failed") from e
    finally:
        session.close()
