"""Pharma service — drug catalog and EDA export business logic."""

from __future__ import annotations

import csv
import hashlib
import io
import os
import tempfile

from datapulse.logging import get_logger
from datapulse.pharma.models import (
    DrugMasterEntry,
    DrugMasterImportResult,
    DrugMasterSearchResult,
    EDAExport,
    EDAExportRequest,
)
from datapulse.pharma.repository import DrugMasterRepository

log = get_logger(__name__)

# Directory used to persist generated CSV files.  Falls back to the
# system temp dir when EDA_EXPORT_DIR is not configured.
_EXPORT_DIR = os.environ.get("EDA_EXPORT_DIR", tempfile.gettempdir())

_CSV_COLUMNS_CONTROLLED = [
    "transaction_id",
    "transaction_date",
    "drug_code",
    "name_en",
    "name_ar",
    "controlled_schedule",
    "atc_code",
    "quantity",
    "unit_price",
    "total_price",
    "staff_id",
    "site_code",
]

_CSV_COLUMNS_MONTHLY = [
    "transaction_id",
    "transaction_date",
    "drug_code",
    "name_en",
    "name_ar",
    "atc_code",
    "controlled_schedule",
    "quantity",
    "unit_price",
    "total_price",
    "staff_id",
    "site_code",
]


def _build_csv(rows: list[dict], columns: list[str]) -> bytes:
    """Serialise *rows* to CSV bytes using *columns* as the header."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data, usedforsecurity=False).hexdigest()


class DrugMasterService:
    """Business logic for the pharma drug catalog and EDA reporting."""

    def __init__(self, repo: DrugMasterRepository) -> None:
        self._repo = repo

    # ── Catalog ────────────────────────────────────────────────────────────

    def search_catalog(self, query: str, limit: int = 50) -> list[DrugMasterSearchResult]:
        """Search the drug catalog by name (EN/AR) or EAN-13."""
        limit = min(max(1, limit), 200)
        return self._repo.search(query, limit)

    def get_by_ean13(self, ean13: str) -> DrugMasterSearchResult | None:
        """Return a single drug by EAN-13 code."""
        return self._repo.get_by_ean13(ean13)

    def import_catalog(self, entries: list[DrugMasterEntry]) -> DrugMasterImportResult:
        """Bulk-import drug catalog entries.

        Entries without an ean13 are skipped; all others are upserted.
        Returns a summary of rows imported and rows skipped.
        """
        log.info("drug_master_import_started", count=len(entries))
        result = self._repo.import_bulk(entries)
        log.info(
            "drug_master_import_finished",
            imported=result.rows_imported,
            skipped=result.rows_skipped,
        )
        return result

    # ── EDA Export ─────────────────────────────────────────────────────────

    def generate_eda_export(
        self,
        tenant_id: int,
        req: EDAExportRequest,
        created_by: str,
    ) -> EDAExport:
        """Generate an EDA CSV export, persist to disk, record in DB.

        Steps:
        1. Query transactions (controlled-only or all-monthly).
        2. Serialise to CSV, compute SHA-256.
        3. Write file to EDA_EXPORT_DIR.
        4. Record metadata in pharma.eda_exports.
        5. Return the new EDAExport record.
        """
        log.info(
            "eda_export_started",
            tenant_id=tenant_id,
            period_start=str(req.period_start),
            period_end=str(req.period_end),
            export_type=req.export_type,
        )

        if req.export_type == "controlled":
            rows = self._repo.fetch_controlled_sales(tenant_id, req.period_start, req.period_end)
            columns = _CSV_COLUMNS_CONTROLLED
        else:
            rows = self._repo.fetch_monthly_sales(tenant_id, req.period_start, req.period_end)
            columns = _CSV_COLUMNS_MONTHLY

        csv_bytes = _build_csv(rows, columns)
        sha256 = _sha256_hex(csv_bytes)

        # Write to disk
        filename = (
            f"eda_{req.export_type}_{tenant_id}"
            f"_{req.period_start}_{req.period_end}"
            f"_{sha256[:8]}.csv"
        )
        file_path = os.path.join(_EXPORT_DIR, filename)
        try:
            with open(file_path, "wb") as fh:
                fh.write(csv_bytes)
        except OSError:
            log.exception("eda_export_write_failed", file_path=file_path)
            file_path = None  # type: ignore[assignment]

        record = self._repo.record_eda_export(
            tenant_id=tenant_id,
            period_start=req.period_start,
            period_end=req.period_end,
            export_type=req.export_type,
            file_path=file_path,
            file_sha256=sha256,
            row_count=len(rows),
            created_by=created_by,
        )

        log.info(
            "eda_export_finished",
            export_id=record.id,
            row_count=len(rows),
            sha256=sha256[:12],
        )
        return record

    # ── EDA History ────────────────────────────────────────────────────────

    def list_eda_exports(self, tenant_id: int) -> list[EDAExport]:
        """Return all past EDA export records for the tenant."""
        return self._repo.list_eda_exports(tenant_id)
