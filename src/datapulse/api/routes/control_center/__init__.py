"""Control Center API — composed of per-resource sub-routers.

The original single-file router was split during the Phase 1
simplification sprint. The public surface — a single `router` mounted
at /control-center — is preserved by including all sub-routers here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from datapulse.api.auth import get_current_user
from datapulse.api.routes.control_center.jobs import router as jobs_router
from datapulse.api.routes.control_center.mappings import router as mappings_router
from datapulse.api.routes.control_center.pipelines import router as pipelines_router
from datapulse.api.routes.control_center.schedules import router as schedules_router
from datapulse.api.routes.control_center.sources import router as sources_router

router = APIRouter(
    prefix="/control-center",
    tags=["control-center"],
    dependencies=[Depends(get_current_user)],
)
router.include_router(sources_router)
router.include_router(pipelines_router)
router.include_router(mappings_router)
router.include_router(jobs_router)
router.include_router(schedules_router)

__all__ = ["router"]
