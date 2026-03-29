"""Pipeline stage executor.

Runs individual pipeline stages (bronze, dbt) and returns results.
No HTTP awareness, no status tracking — pure execution logic.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from uuid import UUID

from datapulse.bronze import loader as bronze_loader
from datapulse.config import Settings
from datapulse.logging import get_logger
from datapulse.pipeline.models import ExecutionResult

log = get_logger(__name__)


class PipelineExecutor:
    """Executes individual pipeline stages."""

    # Allowed dbt selectors (prevents arbitrary dbt command injection)
    ALLOWED_DBT_SELECTORS: frozenset[str] = frozenset({
        "staging",
        "marts",
        "bronze",
        "tag:staging",
        "tag:marts",
        "tag:bronze",
        "stg_sales",
        "dim_date",
        "dim_billing",
        "dim_customer",
        "dim_product",
        "dim_site",
        "dim_staff",
        "fct_sales",
        "agg_sales_daily",
        "agg_sales_monthly",
        "agg_sales_by_product",
        "agg_sales_by_customer",
        "agg_sales_by_site",
        "agg_sales_by_staff",
        "agg_returns",
        "metrics_summary",
    })

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _validate_source_dir(self, source_dir: str) -> Path:
        """Validate source_dir is within the allowed raw_sales_path.

        Prevents path traversal attacks (e.g. "../../etc/passwd").
        """
        allowed_root = Path(self._settings.raw_sales_path).resolve()
        resolved = Path(source_dir).resolve()
        if not (resolved == allowed_root or str(resolved).startswith(str(allowed_root) + "/")):
            raise ValueError(
                f"source_dir '{source_dir}' resolves outside allowed path '{allowed_root}'"
            )
        return resolved

    def _validate_selector(self, selector: str) -> str:
        """Validate dbt selector is in the allowlist."""
        # Support "+" prefix for dbt graph operators
        clean = selector.lstrip("+")
        if clean not in self.ALLOWED_DBT_SELECTORS:
            raise ValueError(
                f"dbt selector '{selector}' is not in the allowed list"
            )
        return selector

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

        try:
            validated_dir = self._validate_source_dir(source_dir)
        except ValueError as exc:
            log.error("executor_bronze_invalid_path", run_id=str(run_id), error=str(exc))
            return ExecutionResult(success=False, error=str(exc), duration_seconds=0.0)

        try:
            df = bronze_loader.run(
                source_dir=validated_dir,
                database_url=self._settings.database_url,
                parquet_path=self._settings.parquet_dir / "bronze_sales.parquet",
                batch_size=self._settings.bronze_batch_size,
            )
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
                error=str(exc),
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
        try:
            selector = self._validate_selector(selector)
        except ValueError as exc:
            log.error("executor_dbt_invalid_selector", run_id=str(run_id), error=str(exc))
            return ExecutionResult(success=False, error=str(exc), duration_seconds=0.0)

        cmd = [
            "dbt", "run",
            "--project-dir", self._settings.dbt_project_dir,
            "--profiles-dir", self._settings.dbt_profiles_dir,
            "--select", selector,
        ]
        log.info("executor_dbt_start", run_id=str(run_id), selector=selector, cmd=" ".join(cmd))
        t0 = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._settings.pipeline_dbt_timeout,
            )
            elapsed = round(time.perf_counter() - t0, 2)

            if proc.returncode != 0:
                error_msg = (
                    proc.stderr.strip()
                    or proc.stdout.strip()
                    or f"dbt exited with code {proc.returncode}"
                )
                log.error("executor_dbt_failed", run_id=str(run_id), error=error_msg)
                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    duration_seconds=elapsed,
                )

            log.info("executor_dbt_done", run_id=str(run_id), selector=selector, seconds=elapsed)
            return ExecutionResult(
                success=True,
                duration_seconds=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = round(time.perf_counter() - t0, 2)
            error_msg = f"dbt {selector} timed out after {self._settings.pipeline_dbt_timeout}s"
            log.error("executor_dbt_timeout", run_id=str(run_id), error=error_msg)
            return ExecutionResult(
                success=False,
                error=error_msg,
                duration_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = round(time.perf_counter() - t0, 2)
            log.error("executor_dbt_error", run_id=str(run_id), error=str(exc))
            return ExecutionResult(
                success=False,
                error=str(exc),
                duration_seconds=elapsed,
            )
