"""Tests for the file watcher module (handler + service)."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch, call

import pytest
from watchdog.events import FileCreatedEvent, FileMovedEvent

from datapulse.watcher.handler import VALID_EXTENSIONS, DEFAULT_DEBOUNCE_SECONDS, DataFileHandler
from datapulse.watcher.service import FileWatcherService


@pytest.fixture(autouse=True)
def _silence_structlog():
    """Patch structlog loggers to avoid 'event' kwarg collision in handler.py."""
    with patch("datapulse.watcher.handler.log", MagicMock()), \
         patch("datapulse.watcher.service.log", MagicMock()):
        yield


# ---------------------------------------------------------------------------
# VALID_EXTENSIONS constant
# ---------------------------------------------------------------------------

class TestValidExtensions:
    """Tests for the VALID_EXTENSIONS constant."""

    def test_contains_csv(self):
        assert ".csv" in VALID_EXTENSIONS

    def test_contains_xlsx(self):
        assert ".xlsx" in VALID_EXTENSIONS

    def test_contains_xls(self):
        assert ".xls" in VALID_EXTENSIONS

    def test_excludes_non_data_extensions(self):
        for ext in (".txt", ".json", ".pdf", ".py", ".zip", ".parquet", ".log"):
            assert ext not in VALID_EXTENSIONS

    def test_is_frozenset(self):
        assert isinstance(VALID_EXTENSIONS, frozenset)

    def test_exactly_three_extensions(self):
        assert len(VALID_EXTENSIONS) == 3


# ---------------------------------------------------------------------------
# DataFileHandler
# ---------------------------------------------------------------------------

class TestDataFileHandlerFileDetection:
    """Test that handler detects data files and ignores non-data files."""

    def _make_handler(self, debounce: float = 0.05) -> tuple[DataFileHandler, MagicMock]:
        callback = MagicMock()
        handler = DataFileHandler(trigger_callback=callback, debounce_seconds=debounce)
        return handler, callback

    def test_csv_file_detected(self):
        handler, callback = self._make_handler()
        event = FileCreatedEvent("/data/raw/sales/report.csv")
        event.is_directory = False
        handler.on_created(event)
        assert "/data/raw/sales/report.csv" in handler._pending_files
        handler.stop()

    def test_xlsx_file_detected(self):
        handler, callback = self._make_handler()
        event = FileCreatedEvent("/data/raw/sales/Q1.xlsx")
        event.is_directory = False
        handler.on_created(event)
        assert "/data/raw/sales/Q1.xlsx" in handler._pending_files
        handler.stop()

    def test_xls_file_detected(self):
        handler, callback = self._make_handler()
        event = FileCreatedEvent("/data/raw/sales/old.xls")
        event.is_directory = False
        handler.on_created(event)
        assert "/data/raw/sales/old.xls" in handler._pending_files
        handler.stop()

    def test_uppercase_extension_detected(self):
        handler, callback = self._make_handler()
        event = FileCreatedEvent("/data/raw/REPORT.CSV")
        event.is_directory = False
        handler.on_created(event)
        assert "/data/raw/REPORT.CSV" in handler._pending_files
        handler.stop()

    def test_non_data_file_ignored(self):
        handler, callback = self._make_handler()
        for path in ["/data/readme.txt", "/data/config.json", "/data/script.py", "/data/notes.pdf"]:
            event = FileCreatedEvent(path)
            event.is_directory = False
            handler.on_created(event)
        assert len(handler._pending_files) == 0
        handler.stop()

    def test_directory_event_ignored(self):
        handler, callback = self._make_handler()
        event = FileCreatedEvent("/data/raw/sales/subdir.csv")
        event.is_directory = True
        handler.on_created(event)
        assert len(handler._pending_files) == 0
        handler.stop()

    def test_no_extension_ignored(self):
        handler, callback = self._make_handler()
        event = FileCreatedEvent("/data/raw/Makefile")
        event.is_directory = False
        handler.on_created(event)
        assert len(handler._pending_files) == 0
        handler.stop()


class TestDataFileHandlerMoved:
    """Test that moved/renamed files are detected via on_moved."""

    def _make_handler(self, debounce: float = 0.05) -> tuple[DataFileHandler, MagicMock]:
        callback = MagicMock()
        handler = DataFileHandler(trigger_callback=callback, debounce_seconds=debounce)
        return handler, callback

    def test_moved_xlsx_detected(self):
        handler, callback = self._make_handler()
        event = FileMovedEvent("/tmp/upload.tmp", "/data/raw/sales/Q2.xlsx")
        event.is_directory = False
        handler.on_moved(event)
        assert "/data/raw/sales/Q2.xlsx" in handler._pending_files
        handler.stop()

    def test_moved_csv_detected(self):
        handler, callback = self._make_handler()
        event = FileMovedEvent("/tmp/tmp123", "/data/raw/data.csv")
        event.is_directory = False
        handler.on_moved(event)
        assert "/data/raw/data.csv" in handler._pending_files
        handler.stop()

    def test_moved_non_data_ignored(self):
        handler, callback = self._make_handler()
        event = FileMovedEvent("/tmp/a.csv", "/data/raw/readme.txt")
        event.is_directory = False
        handler.on_moved(event)
        assert len(handler._pending_files) == 0
        handler.stop()

    def test_moved_directory_ignored(self):
        handler, callback = self._make_handler()
        event = FileMovedEvent("/tmp/old_dir", "/data/raw/new_dir.csv")
        event.is_directory = True
        handler.on_moved(event)
        assert len(handler._pending_files) == 0
        handler.stop()


class TestDataFileHandlerDebounce:
    """Test debounce logic — multiple files within window trigger callback once."""

    def _make_handler(self, debounce: float = 0.1) -> tuple[DataFileHandler, MagicMock]:
        callback = MagicMock()
        handler = DataFileHandler(trigger_callback=callback, debounce_seconds=debounce)
        return handler, callback

    def test_single_file_triggers_callback(self):
        handler, callback = self._make_handler(debounce=0.05)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)
        # Wait for debounce to fire
        time.sleep(0.15)
        callback.assert_called_once()
        files_arg = callback.call_args[0][0]
        assert "/data/raw/a.csv" in files_arg
        handler.stop()

    def test_multiple_files_within_window_trigger_once(self):
        handler, callback = self._make_handler(debounce=0.15)
        for name in ["a.csv", "b.xlsx", "c.xls"]:
            event = FileCreatedEvent(f"/data/raw/{name}")
            event.is_directory = False
            handler.on_created(event)
            time.sleep(0.02)  # small gap, well within debounce window

        # Wait for debounce to fire
        time.sleep(0.3)
        callback.assert_called_once()
        files_arg = callback.call_args[0][0]
        assert len(files_arg) == 3
        handler.stop()

    def test_files_after_debounce_trigger_second_call(self):
        handler, callback = self._make_handler(debounce=0.05)

        # First batch
        event1 = FileCreatedEvent("/data/raw/a.csv")
        event1.is_directory = False
        handler.on_created(event1)
        time.sleep(0.15)  # wait for first debounce to fire

        # Second batch
        event2 = FileCreatedEvent("/data/raw/b.xlsx")
        event2.is_directory = False
        handler.on_created(event2)
        time.sleep(0.15)  # wait for second debounce to fire

        assert callback.call_count == 2
        handler.stop()

    def test_pending_files_cleared_after_trigger(self):
        handler, callback = self._make_handler(debounce=0.05)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)
        time.sleep(0.15)

        assert len(handler._pending_files) == 0
        handler.stop()

    def test_stop_cancels_pending_timer(self):
        handler, callback = self._make_handler(debounce=1.0)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)

        handler.stop()
        time.sleep(0.1)
        # Callback should NOT have fired because we stopped before debounce
        callback.assert_not_called()

    def test_callback_exception_does_not_crash(self):
        callback = MagicMock(side_effect=RuntimeError("network down"))
        handler = DataFileHandler(trigger_callback=callback, debounce_seconds=0.05)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)
        time.sleep(0.15)
        # Should not raise — error is logged
        callback.assert_called_once()
        handler.stop()

    def test_default_debounce_seconds(self):
        assert DEFAULT_DEBOUNCE_SECONDS == 10.0


class TestDataFileHandlerIsDataFile:
    """Test the _is_data_file helper directly."""

    def setup_method(self):
        self.handler = DataFileHandler(trigger_callback=MagicMock())

    def teardown_method(self):
        self.handler.stop()

    @pytest.mark.parametrize("path,expected", [
        ("/data/file.csv", True),
        ("/data/file.xlsx", True),
        ("/data/file.xls", True),
        ("/data/file.CSV", True),
        ("/data/file.XLSX", True),
        ("/data/file.txt", False),
        ("/data/file.json", False),
        ("/data/file.parquet", False),
        ("/data/file", False),
        ("/data/.csv", True),  # hidden file with valid extension
    ])
    def test_is_data_file(self, path: str, expected: bool):
        assert self.handler._is_data_file(path) is expected


# ---------------------------------------------------------------------------
# FileWatcherService
# ---------------------------------------------------------------------------

class TestFileWatcherServiceLifecycle:
    """Test start/stop lifecycle."""

    def _make_settings(self, **overrides) -> MagicMock:
        settings = MagicMock()
        settings.raw_sales_path = "/tmp/test_watch_dir"
        settings.pipeline_webhook_secret = ""
        for k, v in overrides.items():
            setattr(settings, k, v)
        return settings

    @patch("datapulse.watcher.service.Observer")
    def test_start_creates_observer(self, MockObserver):
        mock_observer = MagicMock()
        MockObserver.return_value = mock_observer

        svc = FileWatcherService(settings=self._make_settings())
        svc.start(debounce_seconds=5.0)

        MockObserver.assert_called_once()
        mock_observer.schedule.assert_called_once()
        # Verify the watched directory
        schedule_args = mock_observer.schedule.call_args
        assert schedule_args[0][1] == "/tmp/test_watch_dir"
        assert schedule_args[1]["recursive"] is False
        mock_observer.start.assert_called_once()

        svc.stop()

    @patch("datapulse.watcher.service.Observer")
    def test_stop_joins_observer(self, MockObserver):
        mock_observer = MagicMock()
        MockObserver.return_value = mock_observer

        svc = FileWatcherService(settings=self._make_settings())
        svc.start()
        svc.stop()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5)

    @patch("datapulse.watcher.service.Observer")
    def test_stop_without_start_is_safe(self, MockObserver):
        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise
        svc.stop()

    @patch("datapulse.watcher.service.Observer")
    def test_is_running_before_start(self, MockObserver):
        svc = FileWatcherService(settings=self._make_settings())
        assert svc.is_running is False

    @patch("datapulse.watcher.service.Observer")
    def test_is_running_after_start(self, MockObserver):
        mock_observer = MagicMock()
        mock_observer.is_alive.return_value = True
        MockObserver.return_value = mock_observer

        svc = FileWatcherService(settings=self._make_settings())
        svc.start()
        assert svc.is_running is True
        svc.stop()

    @patch("datapulse.watcher.service.Observer")
    def test_is_running_after_stop(self, MockObserver):
        mock_observer = MagicMock()
        mock_observer.is_alive.return_value = False
        MockObserver.return_value = mock_observer

        svc = FileWatcherService(settings=self._make_settings())
        svc.start()
        svc.stop()
        assert svc.is_running is False

    def test_watch_path_returns_settings_path(self):
        svc = FileWatcherService(settings=self._make_settings(raw_sales_path="/custom/path"))
        assert svc.watch_path == "/custom/path"


class TestFileWatcherServiceTriggerPipeline:
    """Test the _trigger_pipeline HTTP call."""

    def _make_settings(self, **overrides) -> MagicMock:
        settings = MagicMock()
        settings.raw_sales_path = "/app/data/raw/sales"
        settings.pipeline_webhook_secret = ""
        for k, v in overrides.items():
            setattr(settings, k, v)
        return settings

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_posts_to_api(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "abc-123", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings())
        svc._trigger_pipeline(["/data/raw/a.csv", "/data/raw/b.xlsx"])

        mock_httpx.post.assert_called_once()
        call_args = mock_httpx.post.call_args
        assert call_args[0][0] == "http://localhost:8000/api/v1/pipeline/trigger"
        payload = call_args[1]["json"]
        assert payload["source_dir"] == "/app/data/raw/sales"
        assert payload["tenant_id"] == 1
        assert call_args[1]["timeout"] == 30
        mock_resp.raise_for_status.assert_called_once()

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_includes_webhook_secret_header(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(
            settings=self._make_settings(pipeline_webhook_secret="s3cret")
        )
        svc._trigger_pipeline(["/data/raw/a.csv"])

        call_args = mock_httpx.post.call_args
        headers = call_args[1]["headers"]
        assert headers["X-Webhook-Secret"] == "s3cret"

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_no_header_when_secret_empty(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings(pipeline_webhook_secret=""))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        call_args = mock_httpx.post.call_args
        headers = call_args[1]["headers"]
        assert "X-Webhook-Secret" not in headers

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_http_error_does_not_raise(self, mock_httpx):
        import httpx
        mock_httpx.post.side_effect = httpx.HTTPError("Connection refused")
        mock_httpx.HTTPError = httpx.HTTPError

        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise — error is logged internally
        svc._trigger_pipeline(["/data/raw/a.csv"])

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_raise_for_status_error(self, mock_httpx):
        import httpx
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock(),
        )
        mock_httpx.post.return_value = mock_resp
        mock_httpx.HTTPError = httpx.HTTPError

        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise
        svc._trigger_pipeline(["/data/raw/a.csv"])


class TestFileWatcherServiceDefaultSettings:
    """Test that service uses get_settings() when no settings provided."""

    @patch("datapulse.watcher.service.get_settings")
    def test_uses_get_settings_when_none(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.raw_sales_path = "/default/path"
        mock_get_settings.return_value = mock_settings

        svc = FileWatcherService(settings=None)
        assert svc.watch_path == "/default/path"
        mock_get_settings.assert_called_once()
