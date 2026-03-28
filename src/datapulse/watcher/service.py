"""File watcher service — monitors a directory and triggers pipeline via API."""

from __future__ import annotations

import httpx
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
        api_url = f"http://localhost:8000/api/v1/pipeline/trigger"
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
        except httpx.HTTPError as exc:
            log.error("pipeline_trigger_http_error", error=str(exc), files=files)

    @property
    def watch_path(self) -> str:
        return self._settings.raw_sales_path

    def start(self, debounce_seconds: float = 10.0) -> None:
        """Start watching the configured directory."""
        watch_dir = self.watch_path
        log.info("watcher_starting", watch_dir=watch_dir, debounce=debounce_seconds)

        self._handler = DataFileHandler(
            trigger_callback=self._trigger_pipeline,
            debounce_seconds=debounce_seconds,
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
            log.info("watcher_stopped")

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
