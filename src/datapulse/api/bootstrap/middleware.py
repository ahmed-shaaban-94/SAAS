"""HTTP middleware registration — order-sensitive.

FastAPI / Starlette register middleware as a LIFO stack: the LAST
``add_middleware`` or ``@app.middleware("http")`` call becomes the
OUTERMOST wrapper around the router. The order below is deliberate and
MUST NOT be rearranged without understanding the consequences:

1. SlowAPI — per-route ``@limiter.limit`` silently no-ops without it (#539).
2. GZip — compress responses closer to the router.
3. CORS — before security_headers so OPTIONS preflight short-circuits.
4. security_headers — X-Frame-Options / CSP / Referrer-Policy.
5. overload_guard — reject new work early under load (admission control).
6. log_requests — OUTERMOST; request_id must be bound before any
   lifecycle log line and unbound only after ``request_completed``.
"""

import threading
import time
import uuid as _uuid
from collections import deque
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware

from datapulse.api.backpressure import AdmissionController
from datapulse.config import Settings

logger = structlog.get_logger()


#: Origins that the POS desktop app always uses. The embedded Next.js
#: server binds a fixed port (see ``pos-desktop/electron/main.ts:17``), so
#: the origin is constant across every pilot machine. Baking it into the
#: allow-list means deployments don't have to remember to add it to
#: ``CORS_ORIGINS`` — one less operator foot-gun.
POS_DESKTOP_ORIGINS: list[str] = [
    "http://localhost:3847",
    "http://127.0.0.1:3847",
]

# ── Per-route latency histogram (#734) ──────────────────────────────────────
# Key: (method: str, route_template: str, status_code: int)
# Value: deque of duration_ms floats (circular buffer, max 1000 samples)
_route_histogram: dict[tuple[str, str, int], deque[float]] = {}
_histogram_lock = threading.Lock()

_MAX_SAMPLES = 1000


def _record_latency(method: str, route: str, status_code: int, duration_ms: float) -> None:
    """Push one latency sample into the per-route circular buffer."""
    key = (method, route, status_code)
    with _histogram_lock:
        if key not in _route_histogram:
            _route_histogram[key] = deque(maxlen=_MAX_SAMPLES)
        _route_histogram[key].append(duration_ms)


def get_route_percentiles() -> dict[tuple[str, str, int], dict[str, float]]:
    """Return p50 / p95 / p99 latencies for every recorded route.

    Returns an immutable snapshot — callers must not mutate the result.
    """
    result: dict[tuple[str, str, int], dict[str, float]] = {}
    with _histogram_lock:
        snapshot = {k: list(v) for k, v in _route_histogram.items()}

    for key, samples in snapshot.items():
        if not samples:
            continue
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        result[key] = {
            "p50": _percentile(sorted_samples, 50),
            "p95": _percentile(sorted_samples, 95),
            "p99": _percentile(sorted_samples, 99),
            "count": float(n),
        }
    return result


def _percentile(sorted_data: list[float], pct: int) -> float:
    """Nearest-rank percentile from a pre-sorted list."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    # Nearest-rank: index = ceil(pct/100 * n) - 1, clamped to [0, n-1]
    idx = max(0, min(n - 1, int((pct / 100.0) * n + 0.5) - 1))
    return sorted_data[idx]


def install_middleware(app: FastAPI, settings: Settings) -> None:
    """Install the full middleware chain in the canonical order."""
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    # Merge configured origins with the always-allowed POS desktop origins,
    # deduping while preserving order.
    allow_origins = list(dict.fromkeys([*settings.cors_origins, *POS_DESKTOP_ORIGINS]))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
            # POS checkout uses Idempotency-Key to dedupe retries (see
            # src/datapulse/pos/idempotency.py). Preflight must allow it
            # or every POST to /pos/*/checkout returns "Failed to fetch".
            "Idempotency-Key",
            # Pipeline mutations carry this header for webhook auth
            # (see CORS guidance in CLAUDE.md).
            "X-Pipeline-Token",
        ],
    )

    _install_security_headers(app, settings)
    _install_overload_guard(app)
    _install_request_logging(app)


def _install_security_headers(app: FastAPI, settings: Settings) -> None:
    """Embed paths allow iframe embedding; all other paths block it."""

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


def _install_overload_guard(app: FastAPI) -> None:
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


def _install_request_logging(app: FastAPI) -> None:
    """Outermost middleware — guarantees request lifecycle logs carry ``request_id``.

    Previously the bind/unbind of ``request_id`` lived in a separate
    middleware that registered inside this one, so neither
    ``request_started`` nor ``request_completed`` carried the id. Merging
    the two concerns into one outermost middleware keeps the happy-path
    and error-path lifecycle logs correlatable.
    """

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
            status_code = response.status_code if response is not None else 500
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
                user_agent=request.headers.get("user-agent", ""),
            )
            # Record latency sample using the matched route template so that
            # parameterised paths like /pos/transactions/{id}/items are grouped
            # together rather than exploding into one bucket per unique id.
            route: Any = request.scope.get("route")
            route_template: str = route.path if route is not None else request.url.path
            _record_latency(request.method, route_template, status_code, duration_ms)
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            structlog.contextvars.unbind_contextvars("request_id")
