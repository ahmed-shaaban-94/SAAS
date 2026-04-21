"""FastAPI dependencies for billing — tenant plan limits.

Lives in the billing package (not ``api/``) so other business modules can
depend on it without climbing into the api layer (issue #541). Wired into
the FastAPI app via re-export from :mod:`datapulse.api.deps`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from datapulse.billing.plans import PlanLimits, get_plan_limits
from datapulse.billing.repository import BillingRepository
from datapulse.core.auth import CurrentUser, get_tenant_session


def get_tenant_plan_limits(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> PlanLimits:
    """Dependency that returns the current tenant's plan limits.

    Inject into routes that need to enforce plan limits (e.g. pipeline
    trigger, data source creation). Raises HTTP 403 with a clear message
    when a limit would be exceeded.
    """
    tenant_id = int(user.get("tenant_id", "1"))
    repo = BillingRepository(session)
    plan = repo.get_tenant_plan(tenant_id)
    return get_plan_limits(plan)
