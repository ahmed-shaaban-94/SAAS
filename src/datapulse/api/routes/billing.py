"""Billing API endpoints — Stripe, Paymob, InstaPay checkout + webhook + status."""

from __future__ import annotations

from typing import Annotated

import stripe
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import text

from datapulse.api.deps import CurrentUser, build_billing_webhook_service, get_billing_service
from datapulse.api.limiter import limiter
from datapulse.billing.models import (
    BillingStatus,
    CheckoutRequest,
    CheckoutResponse,
    InstapayApproveRequest,
    InstapayUploadRequest,
    PortalResponse,
)
from datapulse.billing.service import BillingService
from datapulse.config import get_settings
from datapulse.core.db import get_session_factory
from datapulse.rbac.dependencies import require_permission

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
@limiter.limit("5/minute")
def create_checkout(
    request: Request,
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
            currency=body.currency,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/portal", response_model=PortalResponse)
@limiter.limit("5/minute")
def create_portal(
    request: Request,
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
    settings = get_settings()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    payload = await request.body()

    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        service = build_billing_webhook_service(session)
        result = service.handle_webhook_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
        session.commit()
        return {"status": result.status, "event_type": result.event_type}
    except stripe.error.SignatureVerificationError as e:
        session.rollback()
        logger.warning("webhook_signature_invalid", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature") from e
    except ValueError as e:
        session.rollback()
        logger.warning("webhook_bad_payload", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except Exception as e:
        session.rollback()
        logger.error("webhook_operational_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed") from e
    finally:
        session.close()


# ── Paymob webhook ────────────────────────────────────────────────────────────


@router.post("/paymob-webhook", include_in_schema=False)
@limiter.limit("60/minute")
async def paymob_webhook(
    request: Request,
    hmac_value: Annotated[str | None, Header(alias="HMAC")] = None,
) -> dict:
    """Handle Paymob transaction notifications. Not behind JWT — HMAC verified."""
    settings = get_settings()

    if not settings.paymob_hmac_secret:
        raise HTTPException(status_code=503, detail="Paymob webhook not configured")

    if not hmac_value:
        raise HTTPException(status_code=400, detail="Missing HMAC header")

    from datapulse.billing.paymob_client import PaymobClient

    payload = await request.body()
    client = PaymobClient(
        api_key=settings.paymob_api_key,
        integration_id=settings.paymob_integration_id,
        iframe_id=settings.paymob_iframe_id,
        hmac_secret=settings.paymob_hmac_secret,
    )

    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        result = client.handle_webhook_event(payload, hmac_value, settings.paymob_hmac_secret)
        if result.status == "completed" and result.plan and result.tenant_id:
            service = build_billing_webhook_service(session)
            service._repo.update_tenant_plan(result.tenant_id, result.plan)
        session.commit()
        return {"status": result.status, "event_type": result.event_type}
    except ValueError as e:
        session.rollback()
        logger.warning("paymob_webhook_invalid", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid payload or HMAC") from e
    except Exception as e:
        session.rollback()
        logger.error("paymob_webhook_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed") from e
    finally:
        session.close()


# ── InstaPay manual reconciliation ───────────────────────────────────────────


@router.post("/instapay/upload-proof", status_code=202)
@limiter.limit("5/minute")
def instapay_upload_proof(
    request: Request,
    body: InstapayUploadRequest,
    user: CurrentUser,
) -> dict:
    """Tenant submits transfer reference + proof URL for admin review."""
    tenant_id = int(user.get("tenant_id", "1"))
    logger.info(
        "instapay_proof_uploaded",
        tenant_id=tenant_id,
        plan=body.plan,
        amount_egp=body.amount_egp,
        reference=body.transfer_reference,
    )
    return {
        "status": "pending_review",
        "message": (
            "Proof received. Your subscription will be activated after admin approval"
            " (typically within 1 business day)."
        ),
        "reference": body.transfer_reference,
    }


@router.post("/instapay/approve", status_code=200)
@limiter.limit("30/minute")
def instapay_approve(
    request: Request,
    body: InstapayApproveRequest,
    user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
    _admin: Annotated[None, Depends(require_permission("billing:admin:approve"))],
) -> dict:
    """Admin activates a tenant subscription after verifying an InstaPay transfer."""
    service._repo.update_tenant_plan(body.tenant_id, body.plan)
    logger.info(
        "instapay_approved",
        tenant_id=body.tenant_id,
        plan=body.plan,
        admin_note=body.admin_note,
        approver=user.get("sub"),
    )
    return {"status": "activated", "tenant_id": body.tenant_id, "plan": body.plan}
