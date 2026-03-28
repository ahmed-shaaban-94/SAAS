"""FastAPI application factory."""

from __future__ import annotations

import time
import traceback

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from datapulse.api.routes import analytics, health
from datapulse.config import get_settings

logger = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title="DataPulse API",
        description="Sales analytics API for DataPulse",
        version="0.1.0",
    )

    # CORS for Next.js dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
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
        return response

    # Register routers
    app.include_router(health.router)
    app.include_router(analytics.router, prefix="/api/v1")

    return app
