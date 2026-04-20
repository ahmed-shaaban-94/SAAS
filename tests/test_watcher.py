"""Tests for the file watcher module (handler + service)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from watchdog.events import FileCreatedEvent, FileMovedEvent

from datapulse.watcher.handler import (
    DEFAULT_DEBOUNCE_SECONDS,
    TEMP_FILE_PREFIXES,
    TEMP_FILE_SUFFIXES,
    VALID_EXTENSIONS,
    DataFileHandler,
    _is_temp_file,
)
from datapulse.watcher.service import FileWatcherService


def _wait_for_callback(
    callback: MagicMock, *, expected_calls: int = 1, timeout: float = 2.0
) -> None:
    """Poll until callback reaches expected call count (avoids flaky sleeps)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if callback.call_count >= expected_calls:
            return
        time.sleep(0.01)
    # Let the assertion happen in the test (will fail with proper message).


@pytest.fixture(autouse=True)
def _silence_structlog():
    """Patch structlog loggers to avoid 'event' kwarg collision in handler.py."""
    with (
        patch("datapulse.watcher.handler.log", MagicMock()),
        patch("datapulse.watcher.service.log", MagicMock()),
    ):
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
        _wait_for_callback(callback)
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

        _wait_for_callback(callback)
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
        _wait_for_callback(callback, expected_calls=1)

        # Second batch
        event2 = FileCreatedEvent("/data/raw/b.xlsx")
        event2.is_directory = False
        handler.on_created(event2)
        _wait_for_callback(callback, expected_calls=2)

        assert callback.call_count == 2
        handler.stop()

    def test_pending_files_cleared_after_trigger(self):
        handler, callback = self._make_handler(debounce=0.05)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)
        _wait_for_callback(callback)

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
        _wait_for_callback(callback)
        # Should not raise — error is logged
        callback.assert_called_once()
        handler.stop()

    def test_default_debounce_seconds(self):
        assert DEFAULT_DEBOUNCE_SECONDS == 10.0


class TestIsTempFile:
    """_is_temp_file must filter partial / lock / OS-managed sidecar files.

    Without this, Excel's `~$*.xlsx` lock files would trigger the pipeline
    on a 1-KB lock instead of the real workbook.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "/data/raw/~$Report.xlsx",
            "/data/raw/~$quarterly.xls",
            "/data/raw/._Report.xlsx",
            "/data/raw/.~Report.xlsx",
            "/data/raw/~backup.csv",
            "/data/raw/upload.tmp",
            "/data/raw/upload.Tmp",  # case-insensitive suffix
            "/data/raw/big.crdownload",
            "/data/raw/big.CRDOWNLOAD",
            "/data/raw/part.part",
            "/data/raw/sheet.lock",
            "/data/raw/draft.filepart",
            "/data/raw/.vimrc.swp",
        ],
    )
    def test_temp_file_detected(self, path: str):
        assert _is_temp_file(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "/data/raw/report.csv",
            "/data/raw/Q1.xlsx",
            "/data/raw/old.xls",
            "/data/raw/PATIENT_data.csv",
            "/data/raw/sales-2026-04-20.xlsx",
            # Not a temp file even though it contains "$" mid-name
            "/data/raw/cost$margins.xlsx",
            # Empty / edge
            "",
            "/data/raw/",
        ],
    )
    def test_real_file_passes(self, path: str):
        assert _is_temp_file(path) is False

    def test_constants_exported(self):
        # Guard against accidental removal — downstream docs / monitoring rely
        # on these sets staying populated.
        assert "~$" in TEMP_FILE_PREFIXES
        assert ".tmp" in TEMP_FILE_SUFFIXES
        assert ".crdownload" in TEMP_FILE_SUFFIXES


class TestTempFileSkipOnEvents:
    """Handler must NOT schedule triggers for temp files, even if the
    extension looks valid. Covers `on_created` + `on_moved`."""

    def _make_handler(self, debounce: float = 0.05) -> tuple[DataFileHandler, MagicMock]:
        callback = MagicMock()
        handler = DataFileHandler(trigger_callback=callback, debounce_seconds=debounce)
        return handler, callback

    @pytest.mark.parametrize(
        "path",
        [
            "/data/raw/~$Report.xlsx",
            "/data/raw/._Quarterly.xlsx",
            "/data/raw/upload.tmp",
            "/data/raw/big.crdownload",
            "/data/raw/part.part",
        ],
    )
    def test_temp_file_not_scheduled_on_create(self, path: str):
        handler, _ = self._make_handler()
        event = FileCreatedEvent(path)
        event.is_directory = False
        handler.on_created(event)
        assert len(handler._pending_files) == 0
        handler.stop()

    def test_temp_file_not_scheduled_on_move(self):
        # A file renamed TO a temp name must still be skipped.
        handler, _ = self._make_handler()
        event = FileMovedEvent("/tmp/source.csv", "/data/raw/~$draft.xlsx")
        event.is_directory = False
        handler.on_moved(event)
        assert len(handler._pending_files) == 0
        handler.stop()

    def test_real_file_after_temp_file_still_detected(self):
        # A temp file event MUST NOT poison the handler for subsequent real events.
        handler, _ = self._make_handler()
        temp_event = FileCreatedEvent("/data/raw/~$lock.xlsx")
        temp_event.is_directory = False
        handler.on_created(temp_event)
        real_event = FileCreatedEvent("/data/raw/report.csv")
        real_event.is_directory = False
        handler.on_created(real_event)
        assert "/data/raw/report.csv" in handler._pending_files
        assert "/data/raw/~$lock.xlsx" not in handler._pending_files
        handler.stop()


class TestDataFileHandlerHealthSnapshot:
    """Handler exposes a lock-safe snapshot for the health endpoint."""

    def test_snapshot_initial_state(self):
        handler = DataFileHandler(trigger_callback=MagicMock(), debounce_seconds=7.5)
        snap = handler.health_snapshot()
        assert snap["pending_files"] == 0
        assert snap["debounce_seconds"] == 7.5
        assert snap["total_triggers"] == 0
        assert snap["last_trigger_at"] is None
        handler.stop()

    def test_snapshot_reflects_pending_files(self):
        handler = DataFileHandler(trigger_callback=MagicMock(), debounce_seconds=5.0)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)
        # File is in `_pending_files` before the debounce fires.
        snap = handler.health_snapshot()
        assert snap["pending_files"] == 1
        handler.stop()

    def test_snapshot_records_trigger_timestamp_iso8601(self):
        callback = MagicMock()
        handler = DataFileHandler(trigger_callback=callback, debounce_seconds=0.03)
        event = FileCreatedEvent("/data/raw/a.csv")
        event.is_directory = False
        handler.on_created(event)
        _wait_for_callback(callback)
        snap = handler.health_snapshot()
        assert snap["total_triggers"] == 1
        assert isinstance(snap["last_trigger_at"], str)
        # Basic ISO-8601 shape check: "YYYY-MM-DDThh:mm:ss".
        assert "T" in snap["last_trigger_at"]
        handler.stop()


class TestDataFileHandlerIsDataFile:
    """Test the _is_data_file helper directly."""

    def setup_method(self):
        self.handler = DataFileHandler(trigger_callback=MagicMock())

    def teardown_method(self):
        self.handler.stop()

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("/data/file.csv", True),
            ("/data/file.xlsx", True),
            ("/data/file.xls", True),
            ("/data/file.CSV", True),
            ("/data/file.XLSX", True),
            ("/data/file.txt", False),
            ("/data/file.json", False),
            ("/data/file.parquet", False),
            ("/data/file", False),
            ("/data/.csv", False),  # dotfile — Path(".csv").suffix is ""
        ],
    )
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
        settings.api_base_url = "http://localhost:8000"
        # Disable the embedded health endpoint by default — tests that
        # exercise it opt in explicitly by overriding this.
        settings.watcher_health_port = 0
        settings.watcher_health_host = "127.0.0.1"
        for k, v in overrides.items():
            setattr(settings, k, v)
        return settings

    @patch("datapulse.watcher.service.Path")
    @patch("datapulse.watcher.service.Observer")
    def test_start_creates_observer(self, mock_observer_cls, mock_path_cls):
        mock_observer = MagicMock()
        mock_observer_cls.return_value = mock_observer
        mock_path_inst = MagicMock()
        mock_path_inst.is_dir.return_value = True
        mock_path_inst.stat.return_value.st_mode = 0o755
        mock_path_cls.return_value = mock_path_inst

        svc = FileWatcherService(settings=self._make_settings())
        svc.start(debounce_seconds=5.0)

        mock_observer_cls.assert_called_once()
        mock_observer.schedule.assert_called_once()
        # Verify the watched directory
        schedule_args = mock_observer.schedule.call_args
        assert schedule_args[0][1] == "/tmp/test_watch_dir"
        assert schedule_args[1]["recursive"] is False
        mock_observer.start.assert_called_once()

        svc.stop()

    @patch("datapulse.watcher.service.Path")
    @patch("datapulse.watcher.service.Observer")
    def test_stop_joins_observer(self, mock_observer_cls, mock_path_cls):
        mock_observer = MagicMock()
        mock_observer_cls.return_value = mock_observer
        mock_path_inst = MagicMock()
        mock_path_inst.is_dir.return_value = True
        mock_path_inst.stat.return_value.st_mode = 0o755
        mock_path_cls.return_value = mock_path_inst

        svc = FileWatcherService(settings=self._make_settings())
        svc.start()
        svc.stop()

        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5)

    @patch("datapulse.watcher.service.Observer")
    def test_stop_without_start_is_safe(self, mock_observer_cls):
        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise
        svc.stop()

    @patch("datapulse.watcher.service.Observer")
    def test_is_running_before_start(self, mock_observer_cls):
        svc = FileWatcherService(settings=self._make_settings())
        assert svc.is_running is False

    @patch("datapulse.watcher.service.Path")
    @patch("datapulse.watcher.service.Observer")
    def test_is_running_after_start(self, mock_observer_cls, mock_path_cls):
        mock_observer = MagicMock()
        mock_observer.is_alive.return_value = True
        mock_observer_cls.return_value = mock_observer
        mock_path_inst = MagicMock()
        mock_path_inst.is_dir.return_value = True
        mock_path_inst.stat.return_value.st_mode = 0o755
        mock_path_cls.return_value = mock_path_inst

        svc = FileWatcherService(settings=self._make_settings())
        svc.start()
        assert svc.is_running is True
        svc.stop()

    @patch("datapulse.watcher.service.Path")
    @patch("datapulse.watcher.service.Observer")
    def test_is_running_after_stop(self, mock_observer_cls, mock_path_cls):
        mock_observer = MagicMock()
        mock_observer.is_alive.return_value = False
        mock_observer_cls.return_value = mock_observer
        mock_path_inst = MagicMock()
        mock_path_inst.is_dir.return_value = True
        mock_path_inst.stat.return_value.st_mode = 0o755
        mock_path_cls.return_value = mock_path_inst

        svc = FileWatcherService(settings=self._make_settings())
        svc.start()
        svc.stop()
        assert svc.is_running is False

    def test_watch_path_returns_settings_path(self):
        svc = FileWatcherService(settings=self._make_settings(raw_sales_path="/custom/path"))
        assert svc.watch_path == "/custom/path"

    def test_start_raises_on_missing_directory(self):
        svc = FileWatcherService(
            settings=self._make_settings(raw_sales_path="/nonexistent/dir/that/does/not/exist")
        )
        with pytest.raises(FileNotFoundError, match="does not exist"):
            svc.start()


class TestFileWatcherServiceTriggerPipeline:
    """Test the _trigger_pipeline HTTP call."""

    def _make_settings(self, **overrides) -> MagicMock:
        settings = MagicMock()
        settings.raw_sales_path = "/app/data/raw/sales"
        settings.pipeline_webhook_secret = ""
        settings.api_base_url = "http://localhost:8000"
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
    def test_trigger_uses_config_api_url(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings(api_base_url="http://api:8000"))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        call_args = mock_httpx.post.call_args
        assert call_args[0][0] == "http://api:8000/api/v1/pipeline/trigger"

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_includes_webhook_secret_header(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings(pipeline_webhook_secret="s3cret"))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        call_args = mock_httpx.post.call_args
        headers = call_args[1]["headers"]
        assert headers["X-Pipeline-Token"] == "s3cret"

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_no_header_when_secret_empty(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings(pipeline_webhook_secret=""))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        call_args = mock_httpx.post.call_args
        headers = call_args[1]["headers"]
        assert "X-Pipeline-Token" not in headers

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_http_error_does_not_raise(self, mock_httpx):
        import httpx as _httpx

        mock_httpx.post.side_effect = _httpx.HTTPError("Connection refused")
        mock_httpx.HTTPError = _httpx.HTTPError

        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise — error is logged internally
        svc._trigger_pipeline(["/data/raw/a.csv"])

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_raise_for_status_error(self, mock_httpx):
        import httpx as _httpx

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock(),
        )
        mock_httpx.post.return_value = mock_resp
        mock_httpx.HTTPError = _httpx.HTTPError

        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise
        svc._trigger_pipeline(["/data/raw/a.csv"])

    @patch("datapulse.watcher.service.httpx")
    def test_trigger_os_error_does_not_raise(self, mock_httpx):
        mock_httpx.post.side_effect = OSError("Network unreachable")

        svc = FileWatcherService(settings=self._make_settings())
        # Should not raise
        svc._trigger_pipeline(["/data/raw/a.csv"])


class TestFileWatcherServiceTenantId:
    """tenant_id flows from `Settings.default_tenant_id` into the trigger
    payload. Before this wiring the watcher hardcoded `tenant_id: 1`, which
    caused multi-tenant deployments to always trigger the pipeline for
    tenant 1 regardless of which tenant's bucket the file landed in."""

    def _make_settings(self, **overrides) -> MagicMock:
        settings = MagicMock()
        settings.raw_sales_path = "/app/data/raw/sales"
        settings.pipeline_webhook_secret = ""
        settings.api_base_url = "http://localhost:8000"
        settings.default_tenant_id = "1"
        for k, v in overrides.items():
            setattr(settings, k, v)
        return settings

    @patch("datapulse.watcher.service.httpx")
    def test_uses_default_tenant_id_from_settings(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings(default_tenant_id="42"))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        payload = mock_httpx.post.call_args[1]["json"]
        assert payload["tenant_id"] == 42

    @patch("datapulse.watcher.service.httpx")
    def test_parses_numeric_string_to_int(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        svc = FileWatcherService(settings=self._make_settings(default_tenant_id="123"))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        payload = mock_httpx.post.call_args[1]["json"]
        assert isinstance(payload["tenant_id"], int)
        assert payload["tenant_id"] == 123

    @patch("datapulse.watcher.service.httpx")
    def test_falls_back_to_1_on_unparseable_value(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        # A typo in .env — `DEFAULT_TENANT_ID=tenant-a` — should not wedge
        # the watcher; it logs a warning and uses 1 (the endpoint will
        # reject the request separately on the API side).
        svc = FileWatcherService(settings=self._make_settings(default_tenant_id="tenant-a"))
        svc._trigger_pipeline(["/data/raw/a.csv"])

        payload = mock_httpx.post.call_args[1]["json"]
        assert payload["tenant_id"] == 1

    @patch("datapulse.watcher.service.httpx")
    def test_falls_back_when_attribute_missing(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"run_id": "x", "status": "running"}
        mock_httpx.post.return_value = mock_resp

        # A minimal settings object (e.g. an older Settings stand-in from
        # another codebase) that doesn't declare `default_tenant_id` at
        # all should still work — fallback to 1.
        class BareSettings:
            raw_sales_path = "/app/data/raw/sales"
            pipeline_webhook_secret = ""
            api_base_url = "http://localhost:8000"
            api_key = ""

        svc = FileWatcherService(settings=BareSettings())  # type: ignore[arg-type]
        svc._trigger_pipeline(["/data/raw/a.csv"])

        payload = mock_httpx.post.call_args[1]["json"]
        assert payload["tenant_id"] == 1


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
