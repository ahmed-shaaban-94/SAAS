"""Watchdog event handler with debouncing for new data files."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
)

from datapulse.logging import get_logger

log = get_logger(__name__)

VALID_EXTENSIONS = frozenset({".csv", ".xlsx", ".xls"})
# Seconds to wait after last file event before triggering (debounce).
DEFAULT_DEBOUNCE_SECONDS = 10.0


class DataFileHandler(FileSystemEventHandler):
    """Watches for new CSV/Excel files and calls a trigger callback after debounce."""

    def __init__(
        self,
        trigger_callback: Callable[[list[str]], None],
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        watch_root: str | None = None,
    ) -> None:
        super().__init__()
        self._trigger_callback = trigger_callback
        self._debounce_seconds = debounce_seconds
        self._watch_root = Path(watch_root).resolve() if watch_root else None
        self._pending_files: set[str] = set()
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        # Health / observability — read under `_lock` from a different thread
        # (the HTTP health server). UTC ISO-8601 when populated.
        self._last_trigger_at: datetime | None = None
        self._total_triggers: int = 0

    def _is_data_file(self, path: str) -> bool:
        """Check if the file has a valid data extension."""
        return Path(path).suffix.lower() in VALID_EXTENSIONS

    def _is_safe_path(self, path: str) -> bool:
        """Verify the resolved path stays within the watch root (no symlink escape)."""
        if self._watch_root is None:
            return True
        try:
            resolved = Path(path).resolve()
            return resolved.is_relative_to(self._watch_root)
        except Exception:
            return False

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._is_data_file(event.src_path) and self._is_safe_path(event.src_path):
            log.info("file_detected", path=event.src_path, event_type="created")
            self._schedule_trigger(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest_path = getattr(event, "dest_path", event.src_path)
        if self._is_data_file(dest_path) and self._is_safe_path(dest_path):
            log.info("file_detected", path=dest_path, event_type="moved")
            self._schedule_trigger(dest_path)

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
        # Record attempt (success OR failure) so health surfaces the fact
        # the watcher reached the trigger path — the callback itself logs
        # its own outcome separately.
        with self._lock:
            self._last_trigger_at = datetime.now(UTC)
            self._total_triggers += 1

    def health_snapshot(self) -> dict[str, object]:
        """Lock-safe snapshot for the health endpoint.

        Returns primitives only so callers can JSON-encode without a custom
        serialiser. `last_trigger_at` is an ISO-8601 string or `None`.
        """
        with self._lock:
            return {
                "pending_files": len(self._pending_files),
                "debounce_seconds": self._debounce_seconds,
                "total_triggers": self._total_triggers,
                "last_trigger_at": (
                    self._last_trigger_at.isoformat() if self._last_trigger_at else None
                ),
            }

    def stop(self) -> None:
        """Cancel any pending timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
