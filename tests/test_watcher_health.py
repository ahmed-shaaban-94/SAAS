"""Tests for the watcher health endpoint (http.server in a daemon thread)."""

from __future__ import annotations

import json
import socket
import time
from http.client import HTTPConnection
from unittest.mock import MagicMock, patch

import pytest

from datapulse.watcher.health import HealthServer


@pytest.fixture(autouse=True)
def _silence_structlog():
    with patch("datapulse.watcher.health.log", MagicMock()):
        yield


def _wait_until_bound(server: HealthServer, timeout: float = 2.0) -> int:
    """Spin until the OS-assigned port is available. Returns the port."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        port = server.bound_port
        if port is not None and port > 0:
            return port
        time.sleep(0.01)
    raise RuntimeError("HealthServer never bound a port")


def _get(port: int, path: str = "/health", timeout: float = 2.0) -> tuple[int, bytes, str]:
    conn = HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        ctype = resp.getheader("Content-Type") or ""
        return resp.status, body, ctype
    finally:
        conn.close()


class TestHealthServerLifecycle:
    def test_start_binds_port_and_stop_releases_it(self):
        snap = MagicMock(return_value={"status": "ok"})
        server = HealthServer(snapshot_fn=snap, host="127.0.0.1", port=0)
        server.start()
        try:
            port = _wait_until_bound(server)
            assert port > 0
            assert server.is_running is True
        finally:
            server.stop()
        assert server.is_running is False
        # Port must be reusable (OS released it).
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))

    def test_start_twice_raises(self):
        server = HealthServer(snapshot_fn=lambda: {"status": "ok"}, port=0)
        server.start()
        try:
            with pytest.raises(RuntimeError, match="already started"):
                server.start()
        finally:
            server.stop()

    def test_stop_before_start_is_safe(self):
        server = HealthServer(snapshot_fn=lambda: {"status": "ok"}, port=0)
        # Calling stop() before start() should be a silent no-op — not an error.
        server.stop()


class TestHealthEndpoint:
    def test_returns_json_payload_from_snapshot(self):
        payload = {
            "status": "ok",
            "watch_dir": "/data/raw",
            "is_running": True,
            "pending_files": 2,
            "debounce_seconds": 10.0,
            "total_triggers": 5,
            "last_trigger_at": "2026-04-20T14:15:22+00:00",
        }
        server = HealthServer(snapshot_fn=lambda: payload, port=0)
        server.start()
        try:
            port = _wait_until_bound(server)
            status, body, ctype = _get(port)
            assert status == 200
            assert ctype.startswith("application/json")
            decoded = json.loads(body)
            assert decoded == payload
        finally:
            server.stop()

    def test_unknown_path_404s(self):
        server = HealthServer(snapshot_fn=lambda: {"status": "ok"}, port=0)
        server.start()
        try:
            port = _wait_until_bound(server)
            status, body, _ = _get(port, path="/nope")
            assert status == 404
            assert b"not found" in body
        finally:
            server.stop()

    def test_snapshot_exception_returns_500_with_error_status(self):
        def boom() -> dict[str, object]:
            raise RuntimeError("snapshot failed")

        server = HealthServer(snapshot_fn=boom, port=0)
        server.start()
        try:
            port = _wait_until_bound(server)
            status, body, ctype = _get(port)
            assert status == 500
            assert ctype.startswith("application/json")
            decoded = json.loads(body)
            assert decoded == {"status": "error"}
        finally:
            server.stop()

    def test_snapshot_called_fresh_on_every_request(self):
        calls = {"n": 0}

        def snap() -> dict[str, object]:
            calls["n"] += 1
            return {"n": calls["n"]}

        server = HealthServer(snapshot_fn=snap, port=0)
        server.start()
        try:
            port = _wait_until_bound(server)
            _get(port)
            _get(port)
            _get(port)
            assert calls["n"] == 3
        finally:
            server.stop()


class TestHealthServerIntegrationWithService:
    """End-to-end: a real FileWatcherService exposes a working health endpoint
    when `watcher_health_port` is set."""

    def test_service_start_exposes_health_endpoint(self, tmp_path):
        # Import here so the service-level `_silence_structlog` autouse from
        # the primary watcher test file doesn't bleed into our test module.
        from datapulse.watcher.service import FileWatcherService

        settings = MagicMock()
        settings.raw_sales_path = str(tmp_path)
        settings.api_base_url = "http://localhost:8000"
        settings.api_key = ""
        settings.pipeline_webhook_secret = ""
        settings.watcher_health_port = 0  # let OS choose
        settings.watcher_health_host = "127.0.0.1"

        with patch("datapulse.watcher.service.log", MagicMock()):
            svc = FileWatcherService(settings=settings)
            # Need port > 0 to actually start, but we want the OS-assigned
            # port semantics — use ephemeral binding via 0 is blocked by
            # our `if port > 0` gate, so pick a random high port instead.
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            settings.watcher_health_port = port
            svc.start(debounce_seconds=0.05)
            try:
                status, body, _ = _get(port)
                assert status == 200
                decoded = json.loads(body)
                assert decoded["watch_dir"] == str(tmp_path)
                assert decoded["is_running"] is True
                assert decoded["status"] == "ok"
                assert decoded["pending_files"] == 0
                assert decoded["last_trigger_at"] is None
                assert decoded["total_triggers"] == 0
            finally:
                svc.stop()

    def test_port_zero_disables_health_server(self, tmp_path):
        from datapulse.watcher.service import FileWatcherService

        settings = MagicMock()
        settings.raw_sales_path = str(tmp_path)
        settings.api_base_url = "http://localhost:8000"
        settings.api_key = ""
        settings.pipeline_webhook_secret = ""
        settings.watcher_health_port = 0  # disabled
        settings.watcher_health_host = "127.0.0.1"

        with patch("datapulse.watcher.service.log", MagicMock()):
            svc = FileWatcherService(settings=settings)
            svc.start(debounce_seconds=0.05)
            try:
                # No server was started — internal field stays None.
                assert svc._health is None
            finally:
                svc.stop()
