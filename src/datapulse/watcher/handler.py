"""Watchdog event handler with debouncing for new data files."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler

from datapulse.logging import get_logger

log = get_logger(__name__)

VALID_EXTENSIONS = frozenset({".csv", ".xlsx", ".xls"})
# Seconds to wait after last file event before triggering (debounce).
DEFAULT_DEBOUNCE_SECONDS = 10.0


class DataFileHandler(FileSystemEventHandler):
    """Watches for new CSV/Excel files and calls a trigger callback after debounce."""

    def __init__(
        self,
        trigger_callback: callable,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    ) -> None:
        super().__init__()
        self._trigger_callback = trigger_callback
        self._debounce_seconds = debounce_seconds
        self._pending_files: set[str] = set()
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _is_data_file(self, path: str) -> bool:
        """Check if the file has a valid data extension."""
        return Path(path).suffix.lower() in VALID_EXTENSIONS

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        if self._is_data_file(event.src_path):
            log.info("file_detected", path=event.src_path, event="created")
            self._schedule_trigger(event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        if self._is_data_file(event.dest_path):
            log.info("file_detected", path=event.dest_path, event="moved")
            self._schedule_trigger(event.dest_path)

    def _schedule_trigger(self, file_path: str) -> None:
        """Debounce: reset timer each time a new file arrives."""
        with self._lock:
            self._pending_files.add(file_path)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._fire_trigger)
            self._timer.daemon = True
            self._timer.start()

    def _fire_trigger(self) -> None:
        """Called after debounce period — triggers pipeline for accumulated files."""
        with self._lock:
            files = list(self._pending_files)
            self._pending_files.clear()
            self._timer = None

        if not files:
            return

        log.info("trigger_firing", file_count=len(files), files=files)
        try:
            self._trigger_callback(files)
        except Exception as exc:
            log.error("trigger_failed", error=str(exc))

    def stop(self) -> None:
        """Cancel any pending timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
