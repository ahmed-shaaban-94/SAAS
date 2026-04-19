"""FastAPI application factory."""

import time
import traceback
import uuid as _uuid

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from datapulse.api.backpressure import AdmissionController
from datapulse.api.limiter import limiter
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
from datapulse.config import get_settings
from datapulse.core.exceptions import (
    DataPulseError,
    QuotaExceededError,
    TenantError,
    ValidationError,
)
from datapulse.logging import setup_logging

logger = structlog.get_logger()


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    from datapulse.scheduler import start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # AsyncIOScheduler.start() must run on the main thread where the
        # asyncio event loop lives — calling it via asyncio.to_thread()
        # causes get_event_loop() to fail in Python 3.12 worker threads,
        # hanging all uvicorn workers at "Waiting for application startup".
        # DB connect_timeout=10s already prevents indefinite hangs.
        try:
            start_scheduler()
        except Exception:
            logger.error("scheduler_start_failed", exc_info=True)
        yield
        stop_scheduler()

    settings = get_settings()
    setup_logging(log_format=settings.log_format)

    # Initialize Sentry error tracking (skipped when DSN is empty)
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            send_default_pii=False,
        )
        logger.info("sentry_initialized", environment=settings.sentry_environment)

    app = FastAPI(
        title="DataPulse API",
        description="Sales analytics API for DataPulse",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.admission_controller = AdmissionController(
        max_in_flight_requests=settings.api_max_in_flight_requests,
        acquire_timeout_ms=settings.api_backpressure_timeout_ms,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Business exception handlers — ordered from most specific to least specific
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(QuotaExceededError)
    async def quota_exceeded_handler(request: Request, exc: QuotaExceededError) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": exc.message})

    @app.exception_handler(TenantError)
    async def tenant_error_handler(request: Request, exc: TenantError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    # POS-specific exception handlers — must be registered BEFORE the generic
    # DataPulseError handler so they take precedence over the catch-all 400.
    from datapulse.pos.exceptions import (
        InsufficientStockError,
        PharmacistVerificationRequiredError,
        ShiftNotOpenError,
        TerminalNotActiveError,
        VoidNotAllowedError,
    )

    @app.exception_handler(InsufficientStockError)
    async def pos_insufficient_stock_handler(
        request: Request, exc: InsufficientStockError
    ) -> JSONResponse:
        logger.info("pos.insufficient_stock", detail=exc.detail)
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(TerminalNotActiveError)
    async def pos_terminal_not_active_handler(
        request: Request, exc: TerminalNotActiveError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(PharmacistVerificationRequiredError)
    async def pos_pharmacist_required_handler(
        request: Request, exc: PharmacistVerificationRequiredError
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    @app.exception_handler(VoidNotAllowedError)
    async def pos_void_not_allowed_handler(
        request: Request, exc: VoidNotAllowedError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(ShiftNotOpenError)
    async def pos_shift_not_open_handler(request: Request, exc: ShiftNotOpenError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(DataPulseError)
    async def datapulse_error_handler(request: Request, exc: DataPulseError) -> JSONResponse:
        logger.warning("datapulse_error", error=exc.message, detail=exc.detail)
        return JSONResponse(status_code=400, content={"detail": exc.message})

    # GZip compression for API responses (minimum 500 bytes)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # CORS for Next.js dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
        ],
    )

    # Security headers middleware
    # Embed paths allow iframe embedding; all other paths block it.
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path.startswith("/api/v1/embed/") and "/token" not in request.url.path:
            embed_origins = " ".join(settings.embed_allowed_origins)
            if embed_origins:
                response.headers["Content-Security-Policy"] = (
                    f"frame-ancestors 'self' {embed_origins}"
                )
            else:
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            response.headers["X-Frame-Options"] = "DENY"
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            raise exc
        logger.error(
            "unhandled_exception",
            method=request.method,
            path=request.url.path,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.middleware("http")
    async def overload_guard_middleware(request: Request, call_next) -> Response:
        controller: AdmissionController = request.app.state.admission_controller
        if controller.is_exempt(request):
            return await call_next(request)

        if not await controller.try_acquire():
            logger.warning(
                "request_rejected_overload",
                method=request.method,
                path=request.url.path,
                in_flight=controller.in_flight,
                limit=controller.max_in_flight_requests,
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is busy. Please retry shortly."},
                headers={
                    "Retry-After": "1",
                    "X-DataPulse-Backpressure": "rejected",
                },
            )

        try:
            response = await call_next(request)
        finally:
            controller.release()

        response.headers["X-DataPulse-Backpressure"] = "guarded"
        return response

    # Request logging + correlation ID.
    #
    # The request_id must be bound BEFORE any lifecycle log line is emitted and
    # unbound only AFTER the "request_completed" log, otherwise the start/end
    # log entries lack the correlation id. Previously request_id was bound in a
    # separate middleware that lived INSIDE this one (registration order put
    # log_requests outermost), so neither "request_started" nor
    # "request_completed" carried the id. The two concerns are now merged into
    # a single outermost middleware to guarantee the happy-path and error-path
    # lifecycle logs are correlatable.
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(_uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status=response.status_code if response is not None else 500,
                duration_ms=duration_ms,
                user_agent=request.headers.get("user-agent", ""),
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            structlog.contextvars.unbind_contextvars("request_id")

    # Register routers
    app.include_router(health.router)
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(pipeline.router, prefix="/api/v1")
    app.include_router(forecasting.router, prefix="/api/v1")
    app.include_router(ai_light.router, prefix="/api/v1")
    app.include_router(queries.router, prefix="/api/v1")
    app.include_router(explore.router, prefix="/api/v1")
    app.include_router(embed.auth_router, prefix="/api/v1")
    app.include_router(embed.public_router, prefix="/api/v1")

    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(targets.router, prefix="/api/v1")
    app.include_router(export.router, prefix="/api/v1")
    app.include_router(billing.router, prefix="/api/v1")
    app.include_router(anomalies.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(leads.router, prefix="/api/v1")
    app.include_router(insights_first.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(views.router, prefix="/api/v1")
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(annotations.router, prefix="/api/v1")
    app.include_router(dashboard_layouts.router, prefix="/api/v1")
    app.include_router(members.router, prefix="/api/v1")
    app.include_router(members.sectors_router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(lineage.router, prefix="/api/v1")
    app.include_router(report_schedules.router, prefix="/api/v1")
    app.include_router(upload.router, prefix="/api/v1")
    app.include_router(scenarios.router, prefix="/api/v1")
    app.include_router(gamification.router, prefix="/api/v1")
    app.include_router(branding.router, prefix="/api/v1")
    app.include_router(branding.public_router, prefix="/api/v1")
    app.include_router(reseller.router, prefix="/api/v1")

    # Pharma platform: Purchase Orders + Suppliers + Margin Analysis
    app.include_router(purchase_orders.router, prefix="/api/v1")
    app.include_router(purchase_orders.margins_router, prefix="/api/v1")
    app.include_router(suppliers.router, prefix="/api/v1")

    # Control Center — behind feature flag; mounts router only when enabled
    if settings.feature_control_center:
        app.include_router(control_center.router, prefix="/api/v1")
        logger.info("control_center_enabled")

    # Pharmaceutical Platform — inventory, expiry, dispensing, POS features
    if settings.feature_platform:
        from datapulse.api.routes import dispensing as dispensing_routes
        from datapulse.api.routes import expiry as expiry_routes
        from datapulse.api.routes import inventory as inventory_routes
        from datapulse.api.routes import pos as pos_routes
        from datapulse.api.routes import promotions as promotion_routes
        from datapulse.api.routes import vouchers as voucher_routes

        app.include_router(inventory_routes.router, prefix="/api/v1")
        app.include_router(expiry_routes.router, prefix="/api/v1")
        app.include_router(dispensing_routes.router, prefix="/api/v1")
        # POS M1: capabilities is a separate unauthenticated router; register
        # it before the main router so OpenAPI groups it correctly.
        app.include_router(pos_routes.capabilities_router, prefix="/api/v1")
        app.include_router(pos_routes.router, prefix="/api/v1")
        app.include_router(voucher_routes.router, prefix="/api/v1")
        app.include_router(promotion_routes.router, prefix="/api/v1")
        logger.info("feature_platform_enabled")

    # Prometheus metrics — exposes /metrics endpoint with HTTP request
    # counters and duration histograms.  Nginx should block external access
    # (only internal/ops scraping).  Excluded paths keep cardinality low.
    Instrumentator(
        excluded_handlers=["/health", "/metrics", "/openapi.json", "/docs"],
        should_group_status_codes=True,
        should_ignore_untemplated=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app
