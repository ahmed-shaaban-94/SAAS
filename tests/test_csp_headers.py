# tests/test_csp_headers.py
"""Validate that CSP headers block unsafe script execution."""

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_security_headers_present(client):
    """API responses include standard security headers."""
    resp = client.get("/health/live")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_no_unsafe_eval_in_api_csp(client):
    """API CSP must never contain unsafe-eval."""
    resp = client.get("/health/live")
    csp = resp.headers.get("content-security-policy", "")
    # The API security middleware may or may not set CSP for this endpoint,
    # but it must NEVER include unsafe-eval regardless
    assert "unsafe-eval" not in csp


def test_api_csp_excludes_unsafe_inline_scripts(client):
    """API CSP must not allow unsafe-inline in script-src."""
    resp = client.get("/health/live")
    csp = resp.headers.get("content-security-policy", "")
    # If CSP is present, verify no unsafe script execution is allowed
    if "script-src" in csp:
        assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
