"""What-if scenario simulation API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_scenario_service
from datapulse.api.limiter import limiter
from datapulse.scenarios.models import ScenarioInput, ScenarioResult
from datapulse.scenarios.service import ScenarioService

router = APIRouter(
    prefix="/scenarios",
    tags=["scenarios"],
    dependencies=[Depends(get_current_user)],
)


ServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]


@router.post("/simulate", response_model=ScenarioResult)
@limiter.limit("20/minute")
def simulate_scenario(
    request: Request,
    body: ScenarioInput,
    service: ServiceDep,
) -> ScenarioResult:
    """Run a what-if simulation with the given adjustments."""
    return service.simulate(body)
