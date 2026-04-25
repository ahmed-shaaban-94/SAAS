"""HTTP-level tests for the RBAC verify-pin endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.routes.rbac import router as rbac_router
from datapulse.core.auth import get_tenant_session
from datapulse.pos.pharmacist_verifier import hash_pin

pytestmark = pytest.mark.unit


MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


def _make_app(session: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(rbac_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_tenant_session] = lambda: session
    return app


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


def _set_pin_match(session: MagicMock, *, matched: bool) -> None:
    """Configure the mock so the SELECT returns a row when ``matched``."""
    chain = MagicMock()
    chain.mappings.return_value.first.return_value = {"?column?": 1} if matched else None
    session.execute.return_value = chain


class TestVerifyPin:
    def test_approved_when_pin_hash_matches_a_member(self, mock_session: MagicMock):
        _set_pin_match(mock_session, matched=True)
        client = TestClient(_make_app(mock_session))
        resp = client.post("/api/v1/rbac/verify-pin", json={"pin": "1234"})
        assert resp.status_code == 200
        assert resp.json() == {"approved": True}

    def test_rejected_when_no_member_matches(self, mock_session: MagicMock):
        _set_pin_match(mock_session, matched=False)
        client = TestClient(_make_app(mock_session))
        resp = client.post("/api/v1/rbac/verify-pin", json={"pin": "9999"})
        assert resp.status_code == 200
        assert resp.json() == {"approved": False}

    def test_validation_rejects_short_pin(self, mock_session: MagicMock):
        _set_pin_match(mock_session, matched=False)
        client = TestClient(_make_app(mock_session))
        resp = client.post("/api/v1/rbac/verify-pin", json={"pin": "1"})
        assert resp.status_code == 422

    def test_validation_rejects_long_pin(self, mock_session: MagicMock):
        _set_pin_match(mock_session, matched=False)
        client = TestClient(_make_app(mock_session))
        resp = client.post("/api/v1/rbac/verify-pin", json={"pin": "1" * 11})
        assert resp.status_code == 422

    def test_query_filters_by_tenant_and_pin_hash(self, mock_session: MagicMock):
        _set_pin_match(mock_session, matched=False)
        client = TestClient(_make_app(mock_session))
        client.post("/api/v1/rbac/verify-pin", json={"pin": "5678"})
        # Inspect the SQL params bound to the SELECT
        params = mock_session.execute.call_args[0][1]
        assert params["tenant_id"] == 1
        assert params["pin_hash"] == hash_pin("5678")
        sql = str(mock_session.execute.call_args[0][0])
        assert "tenant_members" in sql
        assert "pharmacist_pin_hash = :pin_hash" in sql
        assert "is_active           = TRUE" in sql or "is_active = TRUE" in sql
