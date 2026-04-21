"""Observability — Sentry error tracking + Prometheus metrics."""

import sentry_sdk
import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from datapulse.config import Settings

logger = structlog.get_logger()


def init_sentry(settings: Settings) -> None:
    """Initialize Sentry. No-op when ``sentry_dsn`` is empty."""
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )
    logger.info("sentry_initialized", environment=settings.sentry_environment)


def install_prometheus(app: FastAPI) -> None:
    """Expose ``/metrics`` with HTTP request counters + duration histograms.

    Nginx should block external access (internal/ops scraping only). The
    excluded handlers keep cardinality low on health/metadata endpoints.
    """
    Instrumentator(
        excluded_handlers=["/health", "/metrics", "/openapi.json", "/docs"],
        should_group_status_codes=True,
        should_ignore_untemplated=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
