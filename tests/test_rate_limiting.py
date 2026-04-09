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
    """Default rate limit is 60/minute."""
    from datapulse.api.limiter import limiter

    assert len(limiter._default_limits) > 0, "No default limits configured"

    # Iterate LimitGroup objects to find the 60/minute limit
    found = any(
        limit.limit.amount == 60 and limit.limit.multiples == 1
        for limit_group in limiter._default_limits
        for limit in limit_group
        if hasattr(limit, "limit")
    )
    assert found, "Expected to find a 60/minute default rate limit in slowapi limiter"
