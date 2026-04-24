"""OpenTelemetry distributed tracing — optional, disabled by default.

Gates:
    Tracing is a **no-op** unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set.
    The ``opentelemetry.*`` packages are installed via the ``tracing`` extra
    (``pip install 'datapulse[tracing]'``) — if any of them is missing the
    initializer logs a warning and exits cleanly without affecting the app.

Sampling:
    Parent-based traceidratio sampler. Root-span sample rate comes from
    ``OTEL_TRACES_SAMPLER_ARG`` (default ``0.1`` = 10%) so a tracing
    backend upgrade can bump it via env without a redeploy.

Covered instrumentations:
    FastAPI (request/response spans + traceparent propagation), SQLAlchemy
    (all Postgres queries), Redis (cache ops), httpx (outbound calls incl.
    Clerk, Paymob, webhook deliveries).

Covers the ``#607`` acceptance criterion: "A flame graph for a slow
endpoint is available in Tempo/SigNoz within one click of the slow
trace in Grafana."
"""

from __future__ import annotations

import os

from datapulse.logging import get_logger

log = get_logger(__name__)


def _env_sample_rate() -> float:
    """Parse OTEL_TRACES_SAMPLER_ARG; fall back to 10% on bad input."""
    raw = os.environ.get("OTEL_TRACES_SAMPLER_ARG", "0.1")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        log.warning("otel_invalid_sample_rate", raw=raw, fallback=0.1)
        return 0.1
    if value < 0.0 or value > 1.0:
        log.warning("otel_out_of_range_sample_rate", raw=raw, fallback=0.1)
        return 0.1
    return value


def is_tracing_enabled() -> bool:
    """Return True iff OTEL_EXPORTER_OTLP_ENDPOINT is configured."""
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def init_tracing(app=None) -> bool:
    """Initialize OpenTelemetry tracing if the OTLP endpoint is set.

    Args:
        app: Optional FastAPI app instance — when passed, FastAPI
            request spans are auto-instrumented for that app.

    Returns:
        True if tracing was initialized, False if skipped (endpoint
        unset, packages missing, or already initialized).
    """
    if not is_tracing_enabled():
        log.debug("otel_disabled", reason="OTEL_EXPORTER_OTLP_ENDPOINT unset")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError as exc:
        log.warning(
            "otel_packages_missing",
            error=str(exc),
            hint="install with: pip install 'datapulse[tracing]'",
        )
        return False

    # Idempotent: if a TracerProvider other than the default is already
    # installed, assume a prior init_tracing call set it up and skip.
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        log.debug("otel_already_initialized")
        return False

    sample_rate = _env_sample_rate()
    service_name = os.environ.get("OTEL_SERVICE_NAME", "datapulse-api")
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "datapulse",
            "deployment.environment": os.environ.get("SENTRY_ENVIRONMENT", "development"),
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(sample_rate)),
    )
    exporter = OTLPSpanExporter()  # reads OTEL_EXPORTER_OTLP_ENDPOINT from env
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Per-library instrumentation (idempotent inside each library).
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    try:
        from datapulse.core.db import get_engine

        SQLAlchemyInstrumentor().instrument(engine=get_engine())
    except Exception as exc:
        log.warning("otel_sqlalchemy_instrument_failed", error=str(exc))
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    log.info(
        "otel_initialized",
        service_name=service_name,
        sample_rate=sample_rate,
        endpoint_env="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    return True
