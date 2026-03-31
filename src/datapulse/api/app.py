"""FastAPI application factory."""

from __future__ import annotations

import time
import traceback

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from datapulse.api.limiter import limiter
from datapulse.api.routes import ai_light, analytics, embed, explore, health, pipeline, queries
from datapulse.config import get_settings
from datapulse.logging import setup_logging

logger = structlog.get_logger()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(log_format=settings.log_format)

    app = FastAPI(
        title="DataPulse API",
        description="Sales analytics API for DataPulse",
        version="0.1.0",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS for Next.js dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Pipeline-Token"],
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
    app.include_router(ai_light.router, prefix="/api/v1")
    app.include_router(queries.router, prefix="/api/v1")
    app.include_router(explore.router, prefix="/api/v1")
    app.include_router(embed.auth_router, prefix="/api/v1")
    app.include_router(embed.public_router, prefix="/api/v1")

    return app
