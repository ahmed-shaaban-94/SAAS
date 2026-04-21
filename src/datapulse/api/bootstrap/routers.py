"""Router registration — base routers always, feature-flagged routers conditionally.

The ``/health`` router mounts at the root (no ``/api/v1`` prefix) so K8s
probes and the droplet smoke test can hit a stable URL that never moves.
Everything else mounts under ``/api/v1``.
"""

import structlog
from fastapi import FastAPI

from datapulse.api.routes import (
    ai_light,
    analytics,
    annotations,
    anomalies,
    audit,
    billing,
    branding,
    control_center,
    dashboard_layouts,
    embed,
    explore,
    export,
    forecasting,
    gamification,
    health,
    insights_first,
    leads,
    lineage,
    members,
    notifications,
    onboarding,
    pipeline,
    purchase_orders,
    queries,
    report_schedules,
    reports,
    reseller,
    scenarios,
    search,
    suppliers,
    targets,
    upload,
    views,
)
from datapulse.config import Settings

logger = structlog.get_logger()

_API_PREFIX = "/api/v1"


def register_routers(app: FastAPI, settings: Settings) -> None:
    """Mount every router in the order used by the original ``create_app``."""
    app.include_router(health.router)
    _register_core_routers(app)
    _register_pharma_commerce_routers(app)
    _register_feature_flagged_routers(app, settings)


def _register_core_routers(app: FastAPI) -> None:
    """Always-on routers — mounted identically in every deployment."""
    for router in (
        analytics.router,
        pipeline.router,
        forecasting.router,
        ai_light.router,
        queries.router,
        explore.router,
        embed.auth_router,
        embed.public_router,
        reports.router,
        targets.router,
        export.router,
        billing.router,
        anomalies.router,
        onboarding.router,
        leads.router,
        insights_first.router,
        search.router,
        views.router,
        notifications.router,
        annotations.router,
        dashboard_layouts.router,
        members.router,
        members.sectors_router,
        audit.router,
        lineage.router,
        report_schedules.router,
        upload.router,
        scenarios.router,
        gamification.router,
        branding.router,
        branding.public_router,
        reseller.router,
    ):
        app.include_router(router, prefix=_API_PREFIX)


def _register_pharma_commerce_routers(app: FastAPI) -> None:
    """Purchase Orders + Suppliers + Margin Analysis — pharma platform core."""
    app.include_router(purchase_orders.router, prefix=_API_PREFIX)
    app.include_router(purchase_orders.margins_router, prefix=_API_PREFIX)
    app.include_router(suppliers.router, prefix=_API_PREFIX)


def _register_feature_flagged_routers(app: FastAPI, settings: Settings) -> None:
    if settings.feature_control_center:
        app.include_router(control_center.router, prefix=_API_PREFIX)
        logger.info("control_center_enabled")

    if settings.feature_platform:
        # Import lazily so deployments with ``feature_platform=False`` do not
        # pay the import cost of inventory / expiry / dispensing / POS trees.
        from datapulse.api.routes import dispensing as dispensing_routes
        from datapulse.api.routes import expiry as expiry_routes
        from datapulse.api.routes import inventory as inventory_routes
        from datapulse.api.routes import pos as pos_routes
        from datapulse.api.routes import promotions as promotion_routes
        from datapulse.api.routes import vouchers as voucher_routes

        app.include_router(inventory_routes.router, prefix=_API_PREFIX)
        app.include_router(expiry_routes.router, prefix=_API_PREFIX)
        app.include_router(dispensing_routes.router, prefix=_API_PREFIX)
        # POS M1: capabilities is a separate unauthenticated router; register
        # it before the main router so OpenAPI groups it correctly.
        app.include_router(pos_routes.capabilities_router, prefix=_API_PREFIX)
        app.include_router(pos_routes.router, prefix=_API_PREFIX)
        app.include_router(voucher_routes.router, prefix=_API_PREFIX)
        app.include_router(promotion_routes.router, prefix=_API_PREFIX)
        logger.info("feature_platform_enabled")
