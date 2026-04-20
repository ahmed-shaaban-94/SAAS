"""Analytics API — composed of per-domain sub-routers."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from datapulse.api.auth import get_current_user
from datapulse.api.routes.analytics.breakdown import router as breakdown_router
from datapulse.api.routes.analytics.churn import router as churn_router
from datapulse.api.routes.analytics.detail import router as detail_router
from datapulse.api.routes.analytics.health import router as health_router
from datapulse.api.routes.analytics.kpi import router as kpi_router
from datapulse.api.routes.analytics.ranking import router as ranking_router
from datapulse.api.routes.analytics.revenue_forecast import router as revenue_forecast_router

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
)
router.include_router(kpi_router)
router.include_router(ranking_router)
router.include_router(breakdown_router)
router.include_router(churn_router)
router.include_router(health_router)
router.include_router(detail_router)
router.include_router(revenue_forecast_router)

__all__ = ["router"]
