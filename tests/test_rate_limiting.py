"""Verify rate limiting is applied at the API level."""

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_rate_limiter_is_configured(client):
    """The API has a rate limiter attached."""
    app = client.app
    assert hasattr(app.state, "limiter")
    assert app.state.limiter is not None


def test_rate_limit_default_is_sixty_per_minute():
    """Default rate limit is 60/minute (Redis) or 60//workers (fallback)."""
    from datapulse.api.limiter import _WORKERS, limiter

    assert len(limiter._default_limits) > 0, "No default limits configured"

    # Accept either 60 (Redis-backed) or 60//workers (in-memory fallback)
    expected_amounts = {60, max(1, 60 // _WORKERS)}
    found = any(
        limit.limit.amount in expected_amounts and limit.limit.multiples == 1
        for limit_group in limiter._default_limits
        for limit in limit_group
        if hasattr(limit, "limit")
    )
    actual = [
        item.limit.amount
        for grp in limiter._default_limits
        for item in grp
        if hasattr(item, "limit")
    ]
    assert found, f"Expected rate limit of {expected_amounts}/min, got {actual}"
