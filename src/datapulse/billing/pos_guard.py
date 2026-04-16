"""FastAPI dependency: enforce POS plan access.

Usage
-----
Add ``Depends(require_pos_plan())`` to any POS router or individual endpoint
that should only be accessible on the ``platform`` or ``enterprise`` plan.

    router = APIRouter(
        prefix="/pos",
        dependencies=[Depends(get_current_user), Depends(require_pos_plan())],
    )

Returns HTTP 402 (Payment Required) when the tenant's current plan does not
include ``pos_integration = True``.  The error message explicitly names the
upgrade path so the client can surface it in the billing UI.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_plan_limits
from datapulse.billing.plans import PlanLimits


def require_pos_plan() -> Any:
    """Return a FastAPI dependency that enforces ``pos_integration = True``.

    Raises HTTP 402 when the tenant is on a plan that does not include the
    POS module (starter or pro).  Platform and enterprise plans pass through.
    """

    def _check(
        _user: Annotated[dict, Depends(get_current_user)],
        limits: Annotated[PlanLimits, Depends(get_tenant_plan_limits)],
    ) -> None:
        if not limits.pos_integration:
            raise HTTPException(
                status_code=402,
                detail=(
                    "The POS module requires the Platform plan ($99/mo) or higher. "
                    "Upgrade at /billing/plans to unlock POS features."
                ),
            )

    return _check
