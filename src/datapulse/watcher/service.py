"""File watcher service — monitors a directory and triggers pipeline via API."""

from __future__ import annotations

from pathlib import Path

import httpx
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from datapulse.config import Settings, get_settings
from datapulse.logging import get_logger
from datapulse.watcher.handler import DataFileHandler
from datapulse.watcher.health import HealthServer

log = get_logger(__name__)


class FileWatcherService:
    """Watches RAW_SALES_PATH for new data files and triggers the pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._observer: BaseObserver | None = None
        self._handler: DataFileHandler | None = None
        self._health: HealthServer | None = None

    def _resolve_tenant_id(self) -> int:
        """Read the tenant id from `Settings.default_tenant_id`.

        The setting is typed as `str` so it parses safely from env
        (operators who forget to quote `"1"` in `.env` files don't crash
        Pydantic). We coerce to int here; an unparseable value falls back
        to `1` with a warning so a bad env doesn't wedge the watcher
        (the pipeline endpoint will reject the bad tenant anyway).
        """
        raw = getattr(self._settings, "default_tenant_id", "1")
        try:
            return int(raw)
        except (TypeError, ValueError):
            log.warning(
                "invalid_default_tenant_id",
                raw=repr(raw),
                fallback=1,
            )
            return 1

    def _trigger_pipeline(self, files: list[str]) -> None:
        """POST to the pipeline trigger endpoint."""
        api_url = f"{self._settings.api_base_url}/api/v1/pipeline/trigger"
        payload = {
            "source_dir": self._settings.raw_sales_path,
            "tenant_id": self._resolve_tenant_id(),
        }
        headers = {}
        if self._settings.api_key:
            headers["X-API-Key"] = self._settings.api_key
        if self._settings.pipeline_webhook_secret:
            headers["X-Pipeline-Token"] = self._settings.pipeline_webhook_secret

        log.info(
            "triggering_pipeline",
            api_url=api_url,
            file_count=len(files),
            source_dir=self._settings.raw_sales_path,
            tenant_id=payload["tenant_id"],
        )

        try:
            resp = httpx.post(api_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            log.info(
                "pipeline_triggered",
                run_id=data.get("run_id"),
                status=data.get("status"),
                files=files,
            )
        except Exception as exc:
            log.error(
                "pipeline_trigger_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                files=files,
            )

    @property
    def watch_path(self) -> str:
        return self._settings.raw_sales_path

    def start(self, debounce_seconds: float = 10.0) -> None:
        """Start watching the configured directory."""
        watch_dir = self.watch_path

        # Verify directory exists and is accessible
        watch_path = Path(watch_dir)
        if not watch_path.is_dir():
            raise FileNotFoundError(f"Watch directory does not exist: {watch_dir}")
        if not watch_path.stat().st_mode & 0o444:
            raise PermissionError(f"Watch directory is not readable: {watch_dir}")

        log.info(
            "watcher_starting",
            watch_dir=watch_dir,
            debounce=debounce_seconds,
            tenant_id=self._resolve_tenant_id(),
        )

        self._handler = DataFileHandler(
            trigger_callback=self._trigger_pipeline,
            debounce_seconds=debounce_seconds,
            watch_root=watch_dir,
        )
        self._observer = Observer()
        self._observer.schedule(self._handler, watch_dir, recursive=False)
        self._observer.start()

        # Optional health endpoint (port=0 disables). Start AFTER the
        # observer so the `is_running` field reports true on first hit.
        # Read the port defensively: older tests + callers may pass a
        # `Settings` stand-in that doesn't declare the field yet.
        port_raw = getattr(self._settings, "watcher_health_port", 0)
        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            port = 0
        if port > 0:
            host = getattr(self._settings, "watcher_health_host", "127.0.0.1")
            self._health = HealthServer(
                snapshot_fn=self._health_snapshot,
                host=str(host),
                port=port,
            )
            self._health.start()

        log.info("watcher_started", watch_dir=watch_dir)

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        if self._health:
            self._health.stop()
            self._health = None
        if self._handler:
            self._handler.stop()
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            if self._observer.is_alive():
                log.warning("observer_thread_did_not_stop", timeout=5)
            else:
                log.info("watcher_stopped")

    def _health_snapshot(self) -> dict[str, object]:
        """Lock-safe dict for the health endpoint. Combines service-level
        state with the handler's own snapshot."""
        handler_snap: dict[str, object] = self._handler.health_snapshot() if self._handler else {}
        return {
            "status": "ok" if self.is_running else "stopped",
            "watch_dir": self.watch_path,
            "is_running": self.is_running,
            **handler_snap,
        }

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
