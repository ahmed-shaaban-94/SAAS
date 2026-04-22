"""Pharma repository — SQL queries against pharma.drug_master and pharma.eda_exports."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.pharma.models import (
    DrugMasterEntry,
    DrugMasterImportResult,
    DrugMasterSearchResult,
    EDAExport,
)

log = get_logger(__name__)


class DrugMasterRepository:
    """Read/write access to pharma.drug_master and pharma.eda_exports.

    drug_master is a shared catalog (no RLS).
    eda_exports is tenant-scoped via RLS.
    All SQL uses parameterized queries via SQLAlchemy ``text()``.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Drug Catalog ───────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 50) -> list[DrugMasterSearchResult]:
        """ILIKE search on name_en, name_ar, and ean13.

        Returns rows ordered by name_en; active-first.
        """
        pattern = f"%{query}%"
        stmt = text("""
            SELECT
                ean13, name_en, name_ar, strength, form,
                atc_code, controlled_schedule, default_price_egp,
                active_ingredient, is_active,
                created_at, updated_at
            FROM pharma.drug_master
            WHERE (
                name_en ILIKE :pattern
                OR name_ar ILIKE :pattern
                OR ean13 ILIKE :pattern
            )
            ORDER BY is_active DESC, name_en
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, {"pattern": pattern, "limit": limit}).mappings().all()
        return [DrugMasterSearchResult(**dict(r)) for r in rows]

    def get_by_ean13(self, ean13: str) -> DrugMasterSearchResult | None:
        """Return a single drug by EAN-13 code, or None if not found."""
        stmt = text("""
            SELECT
                ean13, name_en, name_ar, strength, form,
                atc_code, controlled_schedule, default_price_egp,
                active_ingredient, is_active,
                created_at, updated_at
            FROM pharma.drug_master
            WHERE ean13 = :ean13
        """)  # noqa: S608

        row = self._session.execute(stmt, {"ean13": ean13}).mappings().first()
        if row is None:
            return None
        return DrugMasterSearchResult(**dict(row))

    def upsert(self, entry: DrugMasterEntry) -> None:
        """Insert or update a drug catalog entry (keyed on ean13)."""
        stmt = text("""
            INSERT INTO pharma.drug_master (
                ean13, name_en, name_ar, strength, form,
                atc_code, controlled_schedule, default_price_egp,
                active_ingredient, is_active, updated_at
            ) VALUES (
                :ean13, :name_en, :name_ar, :strength, :form,
                :atc_code, :controlled_schedule, :default_price_egp,
                :active_ingredient, :is_active, now()
            )
            ON CONFLICT (ean13) DO UPDATE SET
                name_en            = EXCLUDED.name_en,
                name_ar            = EXCLUDED.name_ar,
                strength           = EXCLUDED.strength,
                form               = EXCLUDED.form,
                atc_code           = EXCLUDED.atc_code,
                controlled_schedule = EXCLUDED.controlled_schedule,
                default_price_egp  = EXCLUDED.default_price_egp,
                active_ingredient  = EXCLUDED.active_ingredient,
                is_active          = EXCLUDED.is_active,
                updated_at         = now()
        """)

        self._session.execute(stmt, entry.model_dump())

    def import_bulk(self, entries: list[DrugMasterEntry]) -> DrugMasterImportResult:
        """Batch upsert — rows with no ean13 are skipped.

        Returns a summary with counts of imported and skipped rows.
        """
        imported = 0
        skipped = 0

        for entry in entries:
            if not entry.ean13:
                skipped += 1
                log.debug("drug_master_import_skipped", reason="missing_ean13")
                continue
            try:
                self.upsert(entry)
                imported += 1
            except Exception:
                log.exception("drug_master_upsert_error", ean13=entry.ean13)
                skipped += 1

        log.info("drug_master_bulk_import", imported=imported, skipped=skipped)
        return DrugMasterImportResult(rows_imported=imported, rows_skipped=skipped)

    # ── EDA Exports ────────────────────────────────────────────────────────

    def list_eda_exports(self, tenant_id: int) -> list[EDAExport]:
        """Return all EDA export records for the tenant (RLS-scoped)."""
        stmt = text("""
            SELECT
                id, tenant_id, period_start, period_end,
                export_type, file_path, file_sha256, row_count,
                created_at, created_by
            FROM pharma.eda_exports
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
        """)  # noqa: S608

        rows = self._session.execute(stmt, {"tenant_id": tenant_id}).mappings().all()
        return [EDAExport(**dict(r)) for r in rows]

    def record_eda_export(
        self,
        *,
        tenant_id: int,
        period_start: date,
        period_end: date,
        export_type: str,
        file_path: str | None,
        file_sha256: str | None,
        row_count: int,
        created_by: str,
    ) -> EDAExport:
        """Insert an EDA export record and return the created row."""
        stmt = text("""
            INSERT INTO pharma.eda_exports (
                tenant_id, period_start, period_end, export_type,
                file_path, file_sha256, row_count, created_by
            ) VALUES (
                :tenant_id, :period_start, :period_end, :export_type,
                :file_path, :file_sha256, :row_count, :created_by
            )
            RETURNING
                id, tenant_id, period_start, period_end,
                export_type, file_path, file_sha256, row_count,
                created_at, created_by
        """)

        row = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "period_start": period_start,
                    "period_end": period_end,
                    "export_type": export_type,
                    "file_path": file_path,
                    "file_sha256": file_sha256,
                    "row_count": row_count,
                    "created_by": created_by,
                },
            )
            .mappings()
            .first()
        )

        return EDAExport(**dict(row))  # type: ignore[arg-type]

    # ── EDA raw data helpers ───────────────────────────────────────────────

    def fetch_controlled_sales(
        self,
        tenant_id: int,
        period_start: date,
        period_end: date,
    ) -> list[dict[str, Any]]:
        """Return controlled-substance transactions for the given period.

        Joins pos.transactions with pharma.drug_master on drug_code = ean13
        and filters to controlled_schedule > 0.  Returns raw dicts for CSV
        serialisation in the service layer.
        """
        stmt = text("""
            SELECT
                t.id           AS transaction_id,
                t.transaction_date,
                t.drug_code,
                dm.name_en,
                dm.name_ar,
                dm.controlled_schedule,
                dm.atc_code,
                t.quantity,
                t.unit_price,
                t.total_price,
                t.staff_id,
                t.site_code
            FROM pos.transactions t
            JOIN pharma.drug_master dm
                ON dm.ean13 = t.drug_code
               AND dm.controlled_schedule > 0
            WHERE t.tenant_id = :tenant_id
              AND t.transaction_date >= :period_start
              AND t.transaction_date <= :period_end
            ORDER BY t.transaction_date, t.drug_code
        """)  # noqa: S608

        rows = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "period_start": period_start,
                    "period_end": period_end,
                },
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def fetch_monthly_sales(
        self,
        tenant_id: int,
        period_start: date,
        period_end: date,
    ) -> list[dict[str, Any]]:
        """Return all pharmacy transactions for the given period.

        Used for the 'monthly' EDA report type.
        """
        stmt = text("""
            SELECT
                t.id           AS transaction_id,
                t.transaction_date,
                t.drug_code,
                COALESCE(dm.name_en, t.drug_code) AS name_en,
                dm.name_ar,
                dm.atc_code,
                dm.controlled_schedule,
                t.quantity,
                t.unit_price,
                t.total_price,
                t.staff_id,
                t.site_code
            FROM pos.transactions t
            LEFT JOIN pharma.drug_master dm
                ON dm.ean13 = t.drug_code
            WHERE t.tenant_id = :tenant_id
              AND t.transaction_date >= :period_start
              AND t.transaction_date <= :period_end
            ORDER BY t.transaction_date, t.drug_code
        """)  # noqa: S608

        rows = (
            self._session.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "period_start": period_start,
                    "period_end": period_end,
                },
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]
