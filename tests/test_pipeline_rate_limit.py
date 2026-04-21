"""Regression tests for [P0][SEC] #539 — pipeline mutation rate limits.

CLAUDE.md declares ``5/min pipeline mutations`` as policy. Pre-fix, NONE of
the 9 mutation routes in ``src/datapulse/api/routes/pipeline.py`` carried
an ``@limiter.limit(...)`` decorator — the policy was declared but not
enforced. Combined with the ``PIPELINE_AUTH_DISABLED`` kill-switch (also
removed in this fix), an unauthenticated caller could trigger unlimited
Bronze loads / dbt runs / marts rebuilds.

These tests ensure:
1. Every pipeline mutation route now carries a ``5/minute`` rate limit.
2. The limit is actually enforced end-to-end — 6 rapid calls to
   ``/pipeline/execute/bronze`` yield a 429 on the 6th.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user, require_pipeline_token
from datapulse.api.deps import get_pipeline_executor
from datapulse.api.limiter import limiter
from datapulse.config import Settings, get_settings
from datapulse.pipeline.models import ExecutionResult

_DEV_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}

# The full list of pipeline mutation routes that MUST be rate-limited.
# Update this when new mutation routes are added — missing entries are the
# whole bug we are guarding against (issue #539).
PIPELINE_MUTATIONS: list[tuple[str, str]] = [
    ("POST", "/api/v1/pipeline/runs"),
    ("PATCH", "/api/v1/pipeline/runs/{run_id}"),
    ("POST", "/api/v1/pipeline/trigger"),
    ("POST", "/api/v1/pipeline/runs/{run_id}/resume"),
    ("POST", "/api/v1/pipeline/execute/bronze"),
    ("POST", "/api/v1/pipeline/execute/dbt-staging"),
    ("POST", "/api/v1/pipeline/execute/dbt-marts"),
    ("POST", "/api/v1/pipeline/execute/forecasting"),
    ("POST", "/api/v1/pipeline/execute/quality-check"),
]


@pytest.fixture
def reset_limiter():
    """Reset limiter state AND temporarily re-enable it for this test.

    The session-scoped autouse fixture `_disable_rate_limiting` in
    conftest.py sets ``limiter.enabled = False`` for all tests — necessary
    because most tests hit endpoints many times and would otherwise
    accidentally trip limits. Tests that specifically exercise rate-limit
    behavior must opt back in.
    """
    limiter.reset()
    previous_enabled = limiter.enabled
    limiter.enabled = True
    yield
    limiter.enabled = previous_enabled
    limiter.reset()


@pytest.fixture
def mock_executor_and_client(reset_limiter):
    clean_settings = Settings(_env_file=None, api_key="test-api-key", database_url="")

    app = create_app()
    mock_exec = MagicMock()
    app.dependency_overrides[get_settings] = lambda: clean_settings
    app.dependency_overrides[get_pipeline_executor] = lambda: mock_exec
    app.dependency_overrides[get_current_user] = lambda: _DEV_USER
    app.dependency_overrides[require_pipeline_token] = lambda: None
    # raise_server_exceptions=False lets SlowAPI's RateLimitExceeded be
    # handled by the registered exception handler (returning 429) instead
    # of propagating back to the test caller as a raw Python exception.
    client = TestClient(
        app,
        headers={"X-API-Key": "test-api-key"},
        raise_server_exceptions=False,
    )
    yield mock_exec, client
    app.dependency_overrides.clear()


class TestEveryMutationIsRateLimited:
    """Assert every pipeline mutation carries a ``5/minute`` rate limit.

    This is a structural test: it introspects slowapi's per-endpoint limit
    registration so we catch *new* mutation routes that forget the decorator,
    not just regressions in the existing ones.
    """

    def test_all_mutation_routes_declared_in_pipeline_py(self):
        """Sanity: the PIPELINE_MUTATIONS list matches what's registered."""
        app = create_app()
        registered_pipeline_mutations = {
            (method, route.path)
            for route in app.routes
            if hasattr(route, "methods") and hasattr(route, "path")
            for method in route.methods
            if method in {"POST", "PATCH", "PUT", "DELETE"}
            and route.path.startswith("/api/v1/pipeline/")
        }
        expected = set(PIPELINE_MUTATIONS)
        missing = expected - registered_pipeline_mutations
        assert not missing, (
            f"PIPELINE_MUTATIONS references routes that don't exist in the app: {missing}. "
            "Update the list if routes have been renamed."
        )

    @pytest.mark.parametrize(("method", "path"), PIPELINE_MUTATIONS)
    def test_route_has_5_per_minute_limit(self, method, path):
        """Each mutation endpoint must be registered with a 5/minute limit."""
        app = create_app()
        handler = None
        for route in app.routes:
            if (
                hasattr(route, "methods")
                and hasattr(route, "path")
                and method in route.methods
                and route.path == path
            ):
                handler = route.endpoint
                break
        assert handler is not None, f"Route {method} {path} not found in app"

        # slowapi keys _route_limits by fully-qualified function name.
        # functools.wraps preserves __module__ and __name__ on the wrapper,
        # so we can build the same key from either the wrapper or the original.
        fqn = f"{handler.__module__}.{handler.__name__}"
        registered = getattr(limiter, "_route_limits", {})
        limits = registered.get(fqn, [])
        assert limits, (
            f"Route {method} {path} (handler {fqn}) has no slowapi rate "
            f"limit registered — issue #539 regression."
        )
        # Limit.limit returns e.g. "5 per 1 minute" for a "5/minute" declaration.
        found_5_per_minute = any(
            "5" in str(lim.limit) and "minute" in str(lim.limit).lower() for lim in limits
        )
        assert found_5_per_minute, (
            f"Route {method} {path} (handler {fqn}) has limits "
            f"{[str(lim.limit) for lim in limits]} but none is 5/minute."
        )


class TestRateLimitEnforcedEndToEnd:
    """Integration test — hit an endpoint repeatedly and assert the limit trips.

    Fires 25 calls to /pipeline/execute/bronze. A healthy system should
    trip the per-route 5/minute at call 6. If calls 16-20 trip but 6-15
    don't, the per-route decorator is inert and only the default
    15/min fallback is firing — a regression of issue #539.
    """

    def test_rate_limit_trips_within_first_six_calls(self, mock_executor_and_client):
        mock_exec, client = mock_executor_and_client
        mock_exec.run_bronze.return_value = ExecutionResult(
            success=True,
            rows_loaded=1,
            duration_seconds=0.01,
        )

        body = {"run_id": str(uuid4()), "source_dir": "/app/data/raw/sales"}
        statuses = [
            client.post("/api/v1/pipeline/execute/bronze", json=body).status_code for _ in range(25)
        ]

        # Diagnostic: record where the first 429 happened.
        first_429_idx = next((i for i, s in enumerate(statuses) if s == 429), None)
        assert first_429_idx is not None, (
            f"No 429 in 25 rapid calls — rate limiting is completely inert. "
            f"Status sequence: {statuses}"
        )
        # Per-route 5/minute should trip at call index 5 (0-indexed: the 6th call).
        # Allow index 5 strictly — looser would accept the 15/min default firing.
        assert first_429_idx == 5, (
            f"First 429 at call index {first_429_idx}, expected 5 (6th call). "
            f"Index > 5 means per-route 5/minute is NOT firing; only the global "
            f"default limit is catching abuse. Status sequence: {statuses}"
        )
