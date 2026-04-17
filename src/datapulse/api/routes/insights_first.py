"""First-insight API (Phase 2 Task 3 / #402).

GET /api/v1/insights/first returns the single highest-priority insight
for the current tenant, or `{insight: null}` when the tenant has no
data yet. Cheap by design — the dashboard hook blocks the card on it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.insights_first.models import FirstInsightResponse
from datapulse.insights_first.repository import (
    fetch_mom_change_candidate,
    fetch_top_seller_candidate,
)
from datapulse.insights_first.service import FirstInsightService

router = APIRouter(
    prefix="/insights",
    tags=["insights"],
    dependencies=[Depends(get_current_user)],
)


def get_first_insight_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> FirstInsightService:
    """Wires the production fetchers.

    Order does not matter (the picker enforces priority), but listing them
    by descending priority keeps the configuration readable.

    Active:
    - mom_change  (follow-up #2 / this PR)
    - top_seller  (#402, fallback signal)

    Remaining follow-ups (picker + service already accept new fetchers):
    - expiry_risk, stock_risk.
    """
    return FirstInsightService(
        fetchers=[
            lambda tid: fetch_mom_change_candidate(session, tid),
            lambda tid: fetch_top_seller_candidate(session, tid),
        ],
    )


ServiceDep = Annotated[FirstInsightService, Depends(get_first_insight_service)]


@router.get("/first", response_model=FirstInsightResponse)
@limiter.limit("60/minute")
def get_first_insight(
    request: Request,
    service: ServiceDep,
    user: Annotated[dict, Depends(get_current_user)],
) -> FirstInsightResponse:
    """Return the single best insight for a new user's first dashboard view."""
    tenant_id = int(user.get("tenant_id", 1))
    insight = service.get_first(tenant_id=tenant_id)
    return FirstInsightResponse(insight=insight)
