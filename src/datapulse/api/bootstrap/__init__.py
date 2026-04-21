"""Bootstrap helpers for the FastAPI application factory.

Each helper takes a partially-constructed FastAPI app and wires a focused
concern (middleware, exception handlers, router registration, observability,
lifespan). Keeps ``api/app.py::create_app`` at the 50-line CLAUDE.md ceiling
and makes each helper testable in isolation. Extracted from the 299-line
``create_app`` tracked by issue #544.
"""

from datapulse.api.bootstrap.exceptions import install_exception_handlers
from datapulse.api.bootstrap.lifespan import build_lifespan
from datapulse.api.bootstrap.middleware import install_middleware
from datapulse.api.bootstrap.observability import init_sentry, install_prometheus
from datapulse.api.bootstrap.routers import register_routers

__all__ = [
    "build_lifespan",
    "init_sentry",
    "install_exception_handlers",
    "install_middleware",
    "install_prometheus",
    "register_routers",
]
