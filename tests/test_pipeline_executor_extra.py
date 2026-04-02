"""Extra tests for PipelineExecutor — covers run_dbt edge cases and run_forecasting."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch
from uuid import uuid4

from datapulse.pipeline.executor import PipelineExecutor, _sanitize_error


class TestSanitizeError:
    def test_strips_paths(self):
        result = _sanitize_error("Error at /usr/local/lib/python3.12/site-packages/mod.py")
        assert "/usr/local" not in result

    def test_strips_connection_strings(self):
        result = _sanitize_error("Cannot connect to postgresql://user:pass@host/db")
        assert "postgresql://" not in result
        assert "[redacted]" in result

    def test_truncates_long_errors(self):
        long_error = "x" * 500
        result = _sanitize_error(long_error, max_length=100)
        assert len(result) <= 103  # 100 + "..."
        assert result.endswith("...")

    def test_strips_tracebacks(self):
        error = (
            'Traceback (most recent call last):\n  File "/app/main.py", line 10\nValueError: bad'
        )
        result = _sanitize_error(error)
        assert "Traceback" not in result


class TestRunDbtEdgeCases:
    def _make_executor(self) -> PipelineExecutor:
        settings = MagicMock()
        settings.dbt_project_dir = "/app/dbt"
        settings.dbt_profiles_dir = "/app/dbt"
        settings.pipeline_dbt_timeout = 300
        return PipelineExecutor(settings=settings)

    @patch("datapulse.pipeline.executor.subprocess")
    def test_dbt_failure_stderr_empty_uses_stdout(self, mock_sub):
        """When stderr is empty but returncode != 0, falls back to stdout."""
        mock_sub.run.return_value = MagicMock(
            returncode=1,
            stdout="Some error in stdout",
            stderr="",
        )
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="staging")
        assert result.success is False
        assert result.error is not None

    @patch("datapulse.pipeline.executor.subprocess")
    def test_dbt_failure_both_empty(self, mock_sub):
        """When both stderr and stdout empty, uses generic message."""
        mock_sub.run.return_value = MagicMock(
            returncode=2,
            stdout="",
            stderr="",
        )
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="marts")
        assert result.success is False
        assert "exited with code 2" in result.error

    @patch("datapulse.pipeline.executor.subprocess")
    def test_dbt_generic_exception(self, mock_sub):
        """Non-timeout exceptions are caught."""
        mock_sub.run.side_effect = OSError("command not found")
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="staging")
        assert result.success is False
        assert result.error is not None


class TestRunForecasting:
    def _make_executor(self) -> PipelineExecutor:
        settings = MagicMock()
        settings.database_url = "postgresql://test:test@localhost/test"
        return PipelineExecutor(settings=settings)

    @patch("datapulse.pipeline.executor.get_session_factory")
    @patch("datapulse.forecasting.service.ForecastingService.run_all_forecasts")
    def test_forecasting_success(self, mock_run, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        mock_run.return_value = {"rows_written": 100}

        executor = self._make_executor()
        result = executor.run_forecasting(run_id=uuid4(), tenant_id="1")

        assert result.success is True
        assert result.rows_loaded == 100
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("datapulse.pipeline.executor.get_session_factory")
    @patch("datapulse.forecasting.service.ForecastingService.run_all_forecasts")
    def test_forecasting_failure(self, mock_run, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        mock_run.side_effect = RuntimeError("forecast error")

        executor = self._make_executor()
        result = executor.run_forecasting(run_id=uuid4())

        assert result.success is False
        assert result.error is not None
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
