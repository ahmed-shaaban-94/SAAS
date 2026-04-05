"""FastAPI application factory."""

from __future__ import annotations

import time
import traceback
import uuid as _uuid

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from datapulse.api.limiter import limiter
from datapulse.api.routes import (
    ai_light,
    analytics,
    anomalies,
    billing,
    embed,
    explore,
    export,
    forecasting,
    health,
    pipeline,
    queries,
    reports,
    targets,
)
from datapulse.config import get_settings
from datapulse.logging import setup_logging

logger = structlog.get_logger()


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    from datapulse.scheduler import start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        start_scheduler()
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
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # CORS for Next.js dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Pipeline-Token",
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

    # Request ID middleware — propagates correlation ID across logs
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(_uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        start = time.perf_counter()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            user_agent=request.headers.get("user-agent", ""),
        )
        return response

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

    return app
