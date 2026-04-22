"""POS customer-by-phone lookup route (#624 Phase D3).

Cashier types an Egyptian mobile number; terminal resolves it to a customer,
surfaces loyalty + credit + churn in one payload.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session

from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import CurrentUser
from datapulse.pos.customer_lookup_service import CustomerLookupService
from datapulse.pos.models.customer import PosCustomerLookup

router = APIRouter()


def get_customer_lookup_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> CustomerLookupService:
    """FastAPI factory for :class:`CustomerLookupService`."""
    return CustomerLookupService(session)


@router.get(
    "/customers/by-phone/{phone}",
    response_model=PosCustomerLookup,
    summary="Resolve an Egyptian mobile number to a customer + churn signal",
)
@limiter.limit("60/minute")
def get_customer_by_phone(
    request: Request,
    phone: Annotated[str, Path(min_length=5, max_length=25)],
    user: CurrentUser,
    service: Annotated[
        CustomerLookupService,
        Depends(get_customer_lookup_service),
    ],
) -> PosCustomerLookup:
    """Return the customer matching ``phone`` or 404.

    ``phone`` accepts any of ``01XXXXXXXXX`` / ``201XXXXXXXXX`` /
    ``+201XXXXXXXXX``; the service normalises to E.164 before the DB lookup.
    Invalid shapes and unknown phones both return 404 — the UI treats the
    two cases identically ("No customer found").
    """
    _ = user
    result = service.lookup_by_phone(phone)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No customer found for phone {phone!r}")
    return result
