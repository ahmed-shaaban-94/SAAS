"""Capabilities endpoint tests — feature-only, no tenant state.

The capabilities endpoint is the first thing the POS desktop client hits
when it launches. It must:
  * be reachable without authentication
  * report the server's feature flags
  * NEVER include tenant-scoped data (active_terminals, staff_id, …)

Follows the minimal-app pattern used by ``tests/test_pos_b6a_routes.py``: we
mount only the capabilities router on a fresh FastAPI instance so the test
is fully isolated from the global ``feature_platform`` gating.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


def _make_app() -> FastAPI:
    from datapulse.api.routes.pos import capabilities_router

    app = FastAPI()
    app.state.limiter = None  # placate slowapi if imported transitively
    app.include_router(capabilities_router, prefix="/api/v1")
    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_make_app())


def test_capabilities_returns_required_flags(client: TestClient) -> None:
    r = client.get("/api/v1/pos/capabilities")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["idempotency"] == "v1"
    assert body["capabilities"]["idempotency_key_header"] is True
    assert body["capabilities"]["pos_commit_endpoint"] is True
    assert body["capabilities"]["terminal_device_token"] is True
    assert body["capabilities"]["offline_grant_asymmetric"] is True
    assert body["capabilities"]["multi_terminal_supported"] is False
    assert body["enforced_policies"]["idempotency_ttl_hours"] == 168
    assert body["enforced_policies"]["provisional_ttl_hours"] == 72
    assert body["enforced_policies"]["offline_grant_max_age_hours"] == 12


def test_capabilities_contains_no_tenant_state(client: TestClient) -> None:
    r = client.get("/api/v1/pos/capabilities")
    body = r.json()
    for forbidden in ("tenant_id", "active_terminals", "staff_id", "shift_id"):
        assert forbidden not in body


def test_capabilities_advertises_registration_endpoints(client: TestClient) -> None:
    r = client.get("/api/v1/pos/capabilities")
    body = r.json()
    assert body["tenant_key_endpoint"] == "/api/v1/pos/tenant-key"
    assert body["device_registration_endpoint"] == "/api/v1/pos/terminals/register-device"
