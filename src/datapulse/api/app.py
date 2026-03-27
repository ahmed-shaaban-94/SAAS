"""FastAPI application factory."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from datapulse.api.routes import analytics, health

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
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
        return response

    # Register routers
    app.include_router(health.router)
    app.include_router(analytics.router, prefix="/api/v1")

    return app
