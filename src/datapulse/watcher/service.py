"""File watcher service — monitors a directory and triggers pipeline via API."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from httpx import HTTPError
from watchdog.observers import Observer

from datapulse.config import Settings, get_settings
from datapulse.logging import get_logger
from datapulse.watcher.handler import DataFileHandler

log = get_logger(__name__)


class FileWatcherService:
    """Watches RAW_SALES_PATH for new data files and triggers the pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._observer: Observer | None = None
        self._handler: DataFileHandler | None = None

    def _trigger_pipeline(self, files: list[str]) -> None:
        """POST to the pipeline trigger endpoint."""
        api_url = f"{self._settings.api_base_url}/api/v1/pipeline/trigger"
        payload = {
            "source_dir": self._settings.raw_sales_path,
            "tenant_id": 1,
        }
        headers = {}
        if self._settings.pipeline_webhook_secret:
            headers["X-Webhook-Secret"] = self._settings.pipeline_webhook_secret

        log.info(
            "triggering_pipeline",
            api_url=api_url,
            file_count=len(files),
            source_dir=self._settings.raw_sales_path,
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
        except (HTTPError, json.JSONDecodeError, OSError) as exc:
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

        log.info("watcher_starting", watch_dir=watch_dir, debounce=debounce_seconds)

        self._handler = DataFileHandler(
            trigger_callback=self._trigger_pipeline,
            debounce_seconds=debounce_seconds,
            watch_root=watch_dir,
        )
        self._observer = Observer()
        self._observer.schedule(self._handler, watch_dir, recursive=False)
        self._observer.start()
        log.info("watcher_started", watch_dir=watch_dir)

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        if self._handler:
            self._handler.stop()
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            if self._observer.is_alive():
                log.warning("observer_thread_did_not_stop", timeout=5)
            else:
                log.info("watcher_stopped")

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
