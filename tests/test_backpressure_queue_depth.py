"""Unit tests for the queue-depth backpressure guard."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_guard_allows_when_depth_below_limit(monkeypatch) -> None:
    from datapulse.api.backpressure import QueueDepthGuard

    monkeypatch.setattr("datapulse.api.backpressure.queue_depth", AsyncMock(return_value=5))
    guard = QueueDepthGuard(limit=100)
    assert await guard.allow() is True


@pytest.mark.asyncio
async def test_guard_rejects_when_depth_at_or_above_limit(monkeypatch) -> None:
    from datapulse.api.backpressure import QueueDepthGuard

    monkeypatch.setattr("datapulse.api.backpressure.queue_depth", AsyncMock(return_value=100))
    guard = QueueDepthGuard(limit=100)
    assert await guard.allow() is False


@pytest.mark.asyncio
async def test_guard_disabled_when_limit_zero(monkeypatch) -> None:
    from datapulse.api.backpressure import QueueDepthGuard

    probe = AsyncMock(return_value=999_999)
    monkeypatch.setattr("datapulse.api.backpressure.queue_depth", probe)
    guard = QueueDepthGuard(limit=0)
    assert await guard.allow() is True
    probe.assert_not_awaited()


def test_overload_guard_returns_503_when_queue_full(monkeypatch) -> None:
    from datapulse.api.backpressure import AdmissionController, QueueDepthGuard
    from datapulse.api.bootstrap.middleware import _install_overload_guard

    app = FastAPI()
    app.state.admission_controller = AdmissionController(
        max_in_flight_requests=100, acquire_timeout_ms=10
    )
    monkeypatch.setattr("datapulse.api.backpressure.queue_depth", AsyncMock(return_value=999))
    app.state.queue_depth_guard = QueueDepthGuard(limit=10)
    _install_overload_guard(app)

    @app.get("/api/v1/echo")
    def echo() -> dict:
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/v1/echo")
    assert resp.status_code == 503
    assert resp.headers.get("X-DataPulse-Backpressure") == "rejected"
    assert resp.headers.get("Retry-After") == "1"


def test_overload_guard_passes_when_queue_healthy(monkeypatch) -> None:
    from datapulse.api.backpressure import AdmissionController, QueueDepthGuard
    from datapulse.api.bootstrap.middleware import _install_overload_guard

    app = FastAPI()
    app.state.admission_controller = AdmissionController(
        max_in_flight_requests=100, acquire_timeout_ms=10
    )
    monkeypatch.setattr("datapulse.api.backpressure.queue_depth", AsyncMock(return_value=0))
    app.state.queue_depth_guard = QueueDepthGuard(limit=10)
    _install_overload_guard(app)

    @app.get("/api/v1/echo")
    def echo() -> dict:
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/v1/echo")
    assert resp.status_code == 200
