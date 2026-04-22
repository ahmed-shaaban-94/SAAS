"""POS delivery dispatch + rider routing routes (issue #628).

Sub-router for ``pos.py`` facade.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
    _tenant_id_of,
)
from datapulse.pos.exceptions import RiderNotFoundError, RiderUnavailableError
from datapulse.pos.models.delivery import (
    AvailableRidersResponse,
    CreateDeliveryRequest,
    DeliveryResponse,
)
from datapulse.rbac.dependencies import require_permission

router = APIRouter()


@router.get(
    "/riders/available",
    response_model=AvailableRidersResponse,
    dependencies=[Depends(require_permission("pos:delivery:read"))],
)
@limiter.limit("60/minute")
def list_available_riders(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
) -> AvailableRidersResponse:
    """Return riders currently available for delivery dispatch."""
    return service.list_available_riders(tenant_id=_tenant_id_of(user))


@router.post(
    "/deliveries",
    response_model=DeliveryResponse,
    status_code=201,
    dependencies=[Depends(require_permission("pos:delivery:create"))],
)
@limiter.limit("30/minute")
def create_delivery(
    request: Request,
    body: CreateDeliveryRequest,
    service: ServiceDep,
    user: CurrentUser,
) -> DeliveryResponse:
    """Create a delivery order for a completed transaction.

    Optionally assigns a rider at creation time; marks the rider busy.
    Returns the delivery record with embedded rider details.
    """
    try:
        return service.create_delivery(tenant_id=_tenant_id_of(user), body=body)
    except RiderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except RiderUnavailableError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
