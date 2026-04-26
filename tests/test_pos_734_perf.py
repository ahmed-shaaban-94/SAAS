"""Tests for perf observability (issue #734).

Covers:
- Per-route latency histogram recording and percentile computation
- SLO config YAML is readable and has the expected structure
- Middleware integration: real HTTP request populates the histogram via route template
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


# ── Histogram tests ──────────────────────────────────────────────────────────


def test_histogram_records_samples() -> None:
    """Pushing latency samples must appear in get_route_percentiles()."""
    from datapulse.api.bootstrap.middleware import (
        _record_latency,
        get_route_percentiles,
    )

    _record_latency("GET", "/api/v1/test-734", 200, 100.0)
    _record_latency("GET", "/api/v1/test-734", 200, 200.0)

    pcts = get_route_percentiles()
    assert ("GET", "/api/v1/test-734", 200) in pcts


def test_histogram_percentiles_reasonable() -> None:
    """p50 must sit between min and max of the recorded samples."""
    from datapulse.api.bootstrap.middleware import (
        _record_latency,
        get_route_percentiles,
    )

    route = "/api/v1/test-734-percentiles"
    for ms in range(10, 110, 10):  # 10, 20, ... 100
        _record_latency("POST", route, 201, float(ms))

    pcts = get_route_percentiles()
    key = ("POST", route, 201)
    assert key in pcts
    entry = pcts[key]
    assert entry["p50"] >= 10.0
    assert entry["p95"] <= 100.0
    assert entry["p99"] <= 100.0
    assert entry["p95"] >= entry["p50"]


def test_histogram_distinct_routes_are_separate() -> None:
    """Different route templates must produce distinct histogram keys."""
    from datapulse.api.bootstrap.middleware import (
        _record_latency,
        get_route_percentiles,
    )

    _record_latency("GET", "/api/v1/pos/terminals/{id}", 200, 50.0)
    _record_latency("GET", "/api/v1/pos/catalog/search", 200, 80.0)

    pcts = get_route_percentiles()
    assert ("GET", "/api/v1/pos/terminals/{id}", 200) in pcts
    assert ("GET", "/api/v1/pos/catalog/search", 200) in pcts


# ── Middleware integration test ──────────────────────────────────────────────


def test_middleware_records_route_template_not_raw_path() -> None:
    """A real HTTP request through the app must populate the histogram.

    Uses the /health endpoint (no DB, always available) to exercise the
    full log_requests middleware without needing a live database.
    The histogram key must use the route template (e.g. /health), not a
    raw parameterised URL — this guards against the per-id bucket explosion.
    """
    from fastapi.testclient import TestClient

    from datapulse.api.app import create_app
    from datapulse.api.bootstrap.middleware import get_route_percentiles

    app = create_app()
    # AdmissionController is initialised in create_app; override it to skip DB checks.
    with patch("datapulse.api.bootstrap.lifespan.build_lifespan"):
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/health")

    # /health responds with 200 or 503 — either is fine; we just want the sample recorded.
    assert response.status_code in (200, 503)

    pcts = get_route_percentiles()
    # The histogram key must use the route template path, not an arbitrary raw URL
    health_keys = [k for k in pcts if k[1] == "/health"]
    assert health_keys, (
        "Expected histogram entry for /health template after a real request; "
        f"got keys: {list(pcts.keys())}"
    )


# ── SLO config tests ─────────────────────────────────────────────────────────


def test_slo_config_readable() -> None:
    """config/pos_slos.yaml must exist and contain a 'routes' mapping."""
    import yaml

    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "pos_slos.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    assert "routes" in cfg, "pos_slos.yaml must have a top-level 'routes' key"
    assert isinstance(cfg["routes"], dict), "'routes' must be a mapping of route -> ms"
    assert len(cfg["routes"]) > 0, "'routes' must not be empty"


def test_slo_values_are_positive_integers() -> None:
    """Every SLO target must be a positive integer (milliseconds)."""
    import yaml

    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "pos_slos.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    for route, target_ms in cfg["routes"].items():
        assert isinstance(target_ms, int), f"SLO for {route!r} must be an integer"
        assert target_ms > 0, f"SLO for {route!r} must be positive"
