"""Pipeline stage executor.

Runs individual pipeline stages (bronze, dbt) and returns results.
No HTTP awareness, no status tracking — pure execution logic.
"""

from __future__ import annotations

import re as _re
import subprocess
import time
from pathlib import Path
from uuid import UUID

from datapulse.bronze import loader as bronze_loader
from datapulse.config import Settings
from datapulse.core.db import get_session_factory
from datapulse.logging import get_logger
from datapulse.pipeline.models import ExecutionResult
from datapulse.pipeline.retry import with_retry

log = get_logger(__name__)

_PATH_RE = _re.compile(r"(/[\w./-]+)+")
_CONN_STR_RE = _re.compile(r"postgresql://[^\s]+")
_CLASS_NAME_RE = _re.compile(r"\b[\w.]+(?:Error|Exception|Warning)\b")
_TRACEBACK_RE = _re.compile(r"Traceback \(most recent call last\):.*?(?=\n\S|\Z)", _re.DOTALL)
_FILE_LINE_RE = _re.compile(r'File "[^"]+", line \d+.*')


def _sanitize_error(error: str, max_length: int = 200) -> str:
    """Strip internal paths, connection strings, class names, and tracebacks.

    Prevents leaking server filesystem paths, stack traces, Python class names,
    and database connection strings to external callers.
    """
    sanitized = _TRACEBACK_RE.sub("[traceback]", error)
    sanitized = _FILE_LINE_RE.sub("[traceback]", sanitized)
    sanitized = _CONN_STR_RE.sub("[redacted]", sanitized)
    sanitized = _PATH_RE.sub("[path]", sanitized)
    sanitized = _CLASS_NAME_RE.sub("[error]", sanitized)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


class PipelineExecutor:
    """Executes individual pipeline stages."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_bronze(
        self,
        run_id: UUID,
        source_dir: str,
    ) -> ExecutionResult:
        """Run the bronze loader stage.

        Calls bronze.loader.run() directly (same process).
        """
        log.info("executor_bronze_start", run_id=str(run_id), source_dir=source_dir)
        t0 = time.perf_counter()

        @with_retry(max_attempts=3, base_delay=2.0)
        def _load():
            return bronze_loader.run(
                source_dir=Path(source_dir),
                database_url=self._settings.database_url,
                parquet_path=self._settings.parquet_dir / "bronze_sales.parquet",
                batch_size=self._settings.bronze_batch_size,
            )

        try:
            df = _load()
            elapsed = round(time.perf_counter() - t0, 2)
            rows = df.shape[0]
            log.info("executor_bronze_done", run_id=str(run_id), rows=rows, seconds=elapsed)
            return ExecutionResult(
                success=True,
                rows_loaded=rows,
                duration_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = round(time.perf_counter() - t0, 2)
            log.error("executor_bronze_failed", run_id=str(run_id), error=str(exc))
            return ExecutionResult(
                success=False,
                error=_sanitize_error(str(exc)),
                duration_seconds=elapsed,
            )

    def run_dbt(
        self,
        run_id: UUID,
        selector: str,
    ) -> ExecutionResult:
        """Run a dbt command for the given model selector.

        Uses subprocess since dbt has no stable Python API.
        """
        cmd = [
            "dbt",
            "run",
            "--project-dir",
            self._settings.dbt_project_dir,
            "--profiles-dir",
            self._settings.dbt_profiles_dir,
            "--select",
            selector,
        ]
        log.info(
            "executor_dbt_start",
            run_id=str(run_id),
            selector=selector,
            cmd=" ".join(cmd),
        )
        t0 = time.perf_counter()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=self._settings.pipeline_dbt_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()  # reap zombie
                elapsed = round(time.perf_counter() - t0, 2)
                error_msg = f"dbt {selector} timed out after {self._settings.pipeline_dbt_timeout}s"
                log.error("executor_dbt_timeout", run_id=str(run_id), error=error_msg)
                return ExecutionResult(
                    success=False,
                    error=_sanitize_error(error_msg),
                    duration_seconds=elapsed,
                )

            elapsed = round(time.perf_counter() - t0, 2)

            if proc.returncode != 0:
                raw_error = (
                    stderr.strip() or stdout.strip() or f"dbt exited with code {proc.returncode}"
                )
                log.error("executor_dbt_failed", run_id=str(run_id), error=raw_error)
                return ExecutionResult(
                    success=False,
                    error=_sanitize_error(raw_error),
                    duration_seconds=elapsed,
                )

            log.info(
                "executor_dbt_done",
                run_id=str(run_id),
                selector=selector,
                seconds=elapsed,
            )
            return ExecutionResult(
                success=True,
                duration_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = round(time.perf_counter() - t0, 2)
            log.error("executor_dbt_error", run_id=str(run_id), error=str(exc))
            return ExecutionResult(
                success=False,
                error=_sanitize_error(str(exc)),
                duration_seconds=elapsed,
            )

    def run_forecasting(
        self,
        run_id: UUID,
        tenant_id: str = "1",
    ) -> ExecutionResult:
        """Run the forecasting stage after gold layer completes.

        Executes in-process (like bronze), not as a subprocess.
        Creates its own DB session with tenant isolation.
        """
        from sqlalchemy import text as sa_text

        from datapulse.forecasting.repository import ForecastingRepository
        from datapulse.forecasting.service import ForecastingService

        log.info("executor_forecasting_start", run_id=str(run_id))
        t0 = time.perf_counter()

        session = get_session_factory()()
        try:
            session.execute(sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
            repo = ForecastingRepository(session)
            service = ForecastingService(repo)
            stats = service.run_all_forecasts()
            session.commit()

            elapsed = round(time.perf_counter() - t0, 2)
            rows = stats.get("rows_written", 0)
            log.info(
                "executor_forecasting_done",
                run_id=str(run_id),
                rows=rows,
                seconds=elapsed,
            )
            return ExecutionResult(
                success=True,
                rows_loaded=rows,
                duration_seconds=elapsed,
            )
        except Exception as exc:
            session.rollback()
            elapsed = round(time.perf_counter() - t0, 2)
            log.error("executor_forecasting_failed", run_id=str(run_id), error=str(exc))
            return ExecutionResult(
                success=False,
                error=_sanitize_error(str(exc)),
                duration_seconds=elapsed,
            )
        finally:
            session.close()
