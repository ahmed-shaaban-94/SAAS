"""FastAPI application factory."""

from __future__ import annotations

import time
import traceback

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from datapulse.api.audit import enqueue_audit, start_audit_writer, stop_audit_writer
from datapulse.api.limiter import limiter
from datapulse.api.routes import ai_light, analytics, health, pipeline
from datapulse.config import get_settings

logger = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title="DataPulse API",
        description="Sales analytics API for DataPulse",
        version="0.1.0",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        ),
    )

    # CORS for Next.js dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Webhook-Secret", "X-API-Key"],
    )

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

        # Async audit log (non-blocking) — redact sensitive query params
        safe_params = {
            k: v for k, v in request.query_params.items()
            if k.lower() not in ("api_key", "token", "secret", "password")
        }
        enqueue_audit(
            method=request.method,
            path=request.url.path,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            query_params=safe_params,
            response_status=response.status_code,
            duration_ms=duration_ms,
        )

        return response

    # Startup warnings
    settings = get_settings()
    if not settings.api_key:
        logger.warning(
            "api_key_not_configured",
            msg="API_KEY is empty — all authenticated endpoints will reject requests. "
                "Set API_KEY in your .env file.",
        )

    # Start audit writer (best-effort — no crash if DB not ready)
    if settings.database_url:
        try:
            start_audit_writer(settings.database_url)
        except Exception as exc:
            logger.warning("audit_writer_start_failed", error=str(exc))

    # Graceful shutdown: flush remaining audit records
    @app.on_event("shutdown")
    def shutdown_audit_writer() -> None:
        logger.info("shutting_down_audit_writer")
        stop_audit_writer()

    # Register routers
    app.include_router(health.router)
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(pipeline.router, prefix="/api/v1")
    app.include_router(ai_light.router, prefix="/api/v1")

    return app
