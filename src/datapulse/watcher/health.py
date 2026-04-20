"""Lightweight HTTP health endpoint for the file watcher service.

### Why stdlib + not FastAPI

The watcher runs as a background process with no need for routing, DI,
or async. A `http.server.ThreadingHTTPServer` in a daemon thread keeps
the watcher dep-light (no FastAPI / uvicorn inside the watcher container)
and the footprint under 100 lines.

### What it exposes

`GET /health` → 200 JSON:
```json
{
  "status": "ok",
  "watch_dir": "/app/data/raw/sales",
  "is_running": true,
  "pending_files": 0,
  "debounce_seconds": 10.0,
  "total_triggers": 3,
  "last_trigger_at": "2026-04-20T14:15:22.000+00:00"
}
```

Any other path → 404 with a one-line body.

Docker healthcheck usage:

```yaml
services:
  datapulse-watcher:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8765/health"]
      interval: 30s
      timeout: 3s
      retries: 3
```
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from datapulse.logging import get_logger

log = get_logger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    """Serves a single `/health` endpoint. Other paths 404."""

    # Supplied by `HealthServer._make_handler_class`; typed on the class so
    # mypy/pyright don't complain when the subclass references it.
    snapshot_fn: Callable[[], dict[str, Any]]

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        if self.path != "/health":
            body = b"not found\n"
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            payload = self.snapshot_fn()
        except Exception as exc:  # defensive — snapshot should not throw
            log.error("health_snapshot_failed", error=str(exc))
            body = b'{"status":"error"}\n'
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    # Silence the default stderr access-log line — we want structured
    # logging through the app logger instead.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Skip entirely at info level; a noisy curl loop shouldn't spam
        # the watcher's structured log.
        return


class HealthServer:
    """Wrap a `ThreadingHTTPServer` running in a daemon thread.

    Thread-safe `start()` + `stop()`. Safe to call `stop()` before `start()`
    (no-op). Calling `start()` twice raises `RuntimeError` to surface a
    programming error — the service should only own one server at a time.
    """

    def __init__(
        self,
        snapshot_fn: Callable[[], dict[str, Any]],
        *,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self._snapshot_fn = snapshot_fn
        self._host = host
        self._configured_port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def bound_port(self) -> int | None:
        """Actual port the server is listening on (useful when `port=0`
        was passed so the OS chose one). `None` before `start()`."""
        if self._server is None:
            return None
        return self._server.server_address[1]

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("HealthServer already started")

        handler_cls = self._make_handler_class()
        server = ThreadingHTTPServer((self._host, self._configured_port), handler_cls)
        self._server = server

        def _serve() -> None:
            try:
                server.serve_forever(poll_interval=0.5)
            except Exception as exc:
                log.error("health_server_crashed", error=str(exc))

        thread = threading.Thread(target=_serve, name="watcher-health", daemon=True)
        thread.start()
        self._thread = thread
        log.info("health_server_started", host=self._host, port=self.bound_port)

    def stop(self, timeout: float = 3.0) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server is None:
            return
        try:
            server.shutdown()
            server.server_close()
        except Exception as exc:
            log.warning("health_server_shutdown_error", error=str(exc))
        if thread is not None:
            thread.join(timeout=timeout)
            if thread.is_alive():
                log.warning("health_server_thread_did_not_stop", timeout=timeout)
            else:
                log.info("health_server_stopped")

    def _make_handler_class(self) -> type[_HealthHandler]:
        # The BaseHTTPRequestHandler API instantiates one handler per
        # request; we attach the snapshot callable as a class attribute so
        # the request handler can read it without capturing self.
        snapshot_fn = self._snapshot_fn

        class _BoundHealthHandler(_HealthHandler):
            pass

        _BoundHealthHandler.snapshot_fn = staticmethod(snapshot_fn)
        return _BoundHealthHandler
