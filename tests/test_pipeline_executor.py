"""Tests for PipelineExecutor."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from datapulse.pipeline.executor import PipelineExecutor


class TestRunBronze:
    """Test PipelineExecutor.run_bronze()."""

    def _make_executor(self) -> PipelineExecutor:
        settings = MagicMock()
        settings.database_url = "postgresql://test:test@localhost/test"
        settings.parquet_dir = Path("/tmp/parquet")
        settings.bronze_batch_size = 1000
        settings.pipeline_bronze_timeout = 600
        return PipelineExecutor(settings=settings)

    @patch("datapulse.pipeline.executor.bronze_loader")
    def test_bronze_success(self, mock_loader):
        mock_df = MagicMock()
        mock_df.shape = (50000, 30)
        mock_loader.run.return_value = mock_df

        executor = self._make_executor()
        result = executor.run_bronze(
            run_id=uuid4(),
            source_dir="/app/data/raw/sales",
        )

        assert result.success is True
        assert result.rows_loaded == 50000
        assert result.error is None
        assert result.duration_seconds >= 0
        mock_loader.run.assert_called_once()

    @patch("datapulse.pipeline.executor.bronze_loader")
    def test_bronze_failure(self, mock_loader):
        mock_loader.run.side_effect = FileNotFoundError("No .xlsx files found")

        executor = self._make_executor()
        result = executor.run_bronze(
            run_id=uuid4(),
            source_dir="/nonexistent",
        )

        assert result.success is False
        assert "No .xlsx files found" in result.error
        assert result.rows_loaded is None

    @patch("datapulse.pipeline.executor.bronze_loader")
    def test_bronze_empty_result(self, mock_loader):
        mock_df = MagicMock()
        mock_df.shape = (0, 30)
        mock_loader.run.return_value = mock_df

        executor = self._make_executor()
        result = executor.run_bronze(run_id=uuid4(), source_dir="/app/data")

        assert result.success is True
        assert result.rows_loaded == 0


class TestRunDbt:
    """Test PipelineExecutor.run_dbt()."""

    def _make_executor(self) -> PipelineExecutor:
        settings = MagicMock()
        settings.dbt_project_dir = "/app/dbt"
        settings.dbt_profiles_dir = "/app/dbt"
        settings.pipeline_dbt_timeout = 300
        return PipelineExecutor(settings=settings)

    @patch("datapulse.pipeline.executor.subprocess.Popen")
    def test_dbt_staging_success(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("Completed successfully\n2 of 2 OK", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="staging")

        assert result.success is True
        assert result.error is None
        mock_popen.assert_called_once()

    @patch("datapulse.pipeline.executor.subprocess.Popen")
    def test_dbt_marts_success(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("OK", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="marts")

        assert result.success is True

    @patch("datapulse.pipeline.executor.subprocess.Popen")
    def test_dbt_failure(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "Compilation Error in model stg_sales")
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="staging")

        assert result.success is False
        assert "Compilation" in result.error

    @patch("datapulse.pipeline.executor.subprocess.Popen")
    def test_dbt_timeout(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="dbt run", timeout=300)
        mock_popen.return_value = mock_proc

        executor = self._make_executor()
        result = executor.run_dbt(run_id=uuid4(), selector="staging")

        assert result.success is False
        assert "timed out" in result.error.lower()
