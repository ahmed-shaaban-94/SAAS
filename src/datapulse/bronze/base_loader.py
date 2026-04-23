"""Abstract base class for all bronze-layer data loaders.

Defines the template method pattern: discover -> read -> validate -> load.
Concrete loaders (e.g. ExcelReceiptsLoader) implement the abstract hooks;
the ``run()`` orchestrates the full pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
import structlog
from sqlalchemy import Engine, text

from datapulse.core.db import apply_session_locals

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LoadResult:
    """Immutable result from a single loader run."""

    source_type: str  # e.g. 'excel' | 'pos_api' | 'manual'
    table_name: str  # e.g. 'bronze.stock_receipts'
    rows_loaded: int
    rows_skipped: int
    errors: tuple[str, ...]  # immutable sequence of error messages


class BronzeLoader(ABC):
    """Abstract base for all bronze-layer data loaders.

    Template method pattern: discover -> read -> validate -> load.
    Follows existing bronze/loader.py patterns (parameterized INSERT,
    column whitelisting, batch inserts via Polars).

    Usage::

        class ExcelReceiptsLoader(BronzeLoader):
            def discover(self): ...
            def read(self, source): ...
            def validate(self, df): ...
            def get_column_map(self): ...
            def get_allowed_columns(self): ...
            def get_target_table(self): ...

        result = ExcelReceiptsLoader(data_dir).run(engine, tenant_id=42)
    """

    @abstractmethod
    def discover(self) -> list[Any]:
        """Discover data sources (files, API endpoints, DB cursors, etc.)."""
        ...

    @abstractmethod
    def read(self, source: Any) -> pl.DataFrame:
        """Read a single source into a Polars DataFrame.

        The returned DataFrame should use raw/unmapped column names.
        Column renaming happens in ``validate()``.
        """
        ...

    @abstractmethod
    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Validate, clean, and rename columns in the DataFrame.

        Should apply ``get_column_map()`` renaming and raise ``ValueError``
        on critical schema violations.  Returns cleaned DataFrame with
        only whitelisted columns.
        """
        ...

    @abstractmethod
    def get_column_map(self) -> dict[str, str]:
        """Return Excel header -> DB column name mapping.

        Example::
            {"Receipt Date": "receipt_date", "Drug Code": "drug_code"}
        """
        ...

    @abstractmethod
    def get_allowed_columns(self) -> frozenset[str]:
        """Return the whitelist of allowed DB column names.

        Used to prevent SQL injection: only columns in this set are
        included in the parameterized INSERT statement.
        """
        ...

    @abstractmethod
    def get_target_table(self) -> str:
        """Return the fully-qualified target table name.

        Example: ``'bronze.stock_receipts'``
        """
        ...

    # ── Template method ───────────────────────────────────────

    def run(
        self,
        engine: Engine,
        batch_size: int = 50_000,
        tenant_id: int = 1,
    ) -> LoadResult:
        """Orchestrate discover -> read -> validate -> load.

        Follows the exact pattern of existing ``loader.run()``:
        - Iterates sources returned by ``discover()``
        - Reads each source with ``read()``
        - Validates and cleans with ``validate()``
        - Batch-inserts via parameterized SQL (no f-string queries)
        - Returns an immutable ``LoadResult``
        """
        sources = self.discover()
        table = self.get_target_table()
        allowed = self.get_allowed_columns()

        total_loaded = 0
        total_skipped = 0
        errors: list[str] = []

        for source in sources:
            try:
                raw_df = self.read(source)
                df = self.validate(raw_df)
            except Exception as exc:
                source_name = str(source) if isinstance(source, Path) else repr(source)
                errors.append(f"{source_name}: {exc}")
                logger.warning(
                    "bronze_loader_source_error",
                    table=table,
                    source=source_name,
                    error=str(exc),
                )
                continue

            # Filter to whitelisted columns only (injection prevention)
            cols = [c for c in df.columns if c in allowed]
            if not cols:
                errors.append(f"No whitelisted columns found in {source}")
                continue

            df = df.select(cols).with_columns(pl.lit(tenant_id).alias("tenant_id"))

            # Batch insert
            rows = df.to_dicts()
            col_list = ", ".join(df.columns)
            placeholders = ", ".join(f":{c}" for c in df.columns)
            insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"  # noqa: S608

            with engine.begin() as conn:
                apply_session_locals(conn, tenant_id=tenant_id, statement_timeout=None)
                for i in range(0, len(rows), batch_size):
                    batch = rows[i : i + batch_size]
                    conn.execute(text(insert_sql), batch)

            total_loaded += len(rows)

        return LoadResult(
            source_type=self._source_type(),
            table_name=table,
            rows_loaded=total_loaded,
            rows_skipped=total_skipped,
            errors=tuple(errors),
        )

    def _source_type(self) -> str:
        """Infer source type label from class name for LoadResult."""
        name = type(self).__name__.lower()
        if "excel" in name or "xlsx" in name:
            return "excel"
        if "api" in name or "pos" in name:
            return "pos_api"
        return "manual"
