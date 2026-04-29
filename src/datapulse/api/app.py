"""FastAPI application factory.

Keeps the top-level factory short by delegating to the ``api.bootstrap``
helpers. Each helper owns one concern (middleware, exception handlers,
routers, observability, lifespan). See ``api/bootstrap/*.py`` for the
ordering rules that must be preserved when changing any step.
"""

import structlog
from fastapi import FastAPI

from datapulse.api.backpressure import AdmissionController, QueueDepthGuard
from datapulse.api.bootstrap import (
    build_lifespan,
    init_sentry,
    install_exception_handlers,
    install_middleware,
    install_prometheus,
    register_routers,
)
from datapulse.api.limiter import limiter
from datapulse.config import get_settings
from datapulse.logging import setup_logging
from datapulse.tracing import init_tracing

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()
    setup_logging(log_format=settings.log_format)
    init_sentry(settings)

    app = FastAPI(
        title="DataPulse API",
        description="Sales analytics API for DataPulse",
        version="0.1.0",
        lifespan=build_lifespan(),
    )
    app.state.admission_controller = AdmissionController(
        max_in_flight_requests=settings.api_max_in_flight_requests,
        acquire_timeout_ms=settings.api_backpressure_timeout_ms,
    )
    app.state.queue_depth_guard = QueueDepthGuard(limit=settings.arq_queue_depth_limit)
    app.state.limiter = limiter

    install_exception_handlers(app)
    install_middleware(app, settings)
    register_routers(app, settings)
    install_prometheus(app)
    # OpenTelemetry tracing (#607). No-op unless OTEL_EXPORTER_OTLP_ENDPOINT
    # is set AND the 'tracing' extra is installed — keeps default deploys
    # lightweight while giving ops a single env-var switch to turn it on.
    init_tracing(app)
    return app
