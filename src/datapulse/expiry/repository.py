"""Expiry repository — parameterized SQL queries against the gold layer."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.core.sql import build_where, build_where_eq
from datapulse.expiry.models import (
    BatchInfo,
    ExpiryAlert,
    ExpiryCalendarDay,
    ExpiryExposureTier,
    ExpiryFilter,
    ExpirySummary,
    QuarantineRequest,
    WriteOffRequest,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_SCHEMA = "public_marts"


class ExpiryRepository:
    """Read/write access to expiry data — dim_batch, feat_expiry_alerts, agg_expiry_summary.

    All SQL uses parameterized queries via SQLAlchemy ``text()``.
    Write operations mutate bronze.batches directly; dbt picks them up
    on the next pipeline run.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Batch List ─────────────────────────────────────────────────────────

    def get_batches(self, filters: ExpiryFilter) -> list[BatchInfo]:
        """Return batches from dim_batch with computed alert_level."""
        where, params = build_where_eq(
            [
                ("b.site_code", "site_code", filters.site_code),
                ("b.drug_code", "drug_code", filters.drug_code),
            ],
            extra_clauses=["b.batch_key != -1", "b.current_quantity > 0"],
        )
        # alert_level is a derived bucket with its own parameterized CASE —
        # kept inline because the helper only supports simple comparisons.
        if filters.alert_level is not None:
            where += (
                " AND CASE"
                " WHEN b.days_to_expiry <= 0 THEN 'expired'"
                " WHEN b.days_to_expiry <= 30 THEN 'critical'"
                " WHEN b.days_to_expiry <= 60 THEN 'warning'"
                " WHEN b.days_to_expiry <= 90 THEN 'caution'"
                " ELSE 'safe' END = :alert_level"
            )
            params["alert_level"] = filters.alert_level

        where_clause = f"WHERE {where}"
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                b.batch_key,
                b.drug_code,
                COALESCE(p.drug_name, b.drug_code)  AS drug_name,
                b.site_code,
                b.batch_number,
                b.expiry_date,
                b.current_quantity,
                b.days_to_expiry,
                CASE
                    WHEN b.days_to_expiry <= 0  THEN 'expired'
                    WHEN b.days_to_expiry <= 30 THEN 'critical'
                    WHEN b.days_to_expiry <= 60 THEN 'warning'
                    WHEN b.days_to_expiry <= 90 THEN 'caution'
                    ELSE 'safe'
                END AS alert_level,
                b.computed_status
            FROM {_SCHEMA}.dim_batch b
            LEFT JOIN {_SCHEMA}.dim_product p
                ON b.drug_code = p.drug_code AND b.tenant_id = p.tenant_id
            {where_clause}
            ORDER BY b.expiry_date ASC, b.drug_code
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [BatchInfo(**dict(r)) for r in rows]

    def get_batches_by_drug(self, drug_code: str, filters: ExpiryFilter) -> list[BatchInfo]:
        """Return all batches for a specific drug."""
        updated = ExpiryFilter(**{**filters.model_dump(), "drug_code": drug_code})
        return self.get_batches(updated)

    # ── Expiry Alerts ──────────────────────────────────────────────────────

    def get_near_expiry(self, days_threshold: int, filters: ExpiryFilter) -> list[ExpiryAlert]:
        """Return batches expiring within ``days_threshold`` days from feat_expiry_alerts."""
        where, params = build_where(
            [
                ("b.days_to_expiry", "<=", "days_threshold", days_threshold),
                ("b.site_code", "=", "site_code", filters.site_code),
                ("b.drug_code", "=", "drug_code", filters.drug_code),
            ],
            extra_clauses=["b.current_quantity > 0"],
        )
        where_clause = f"WHERE {where}"
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                b.drug_code,
                b.drug_name,
                b.drug_brand,
                b.batch_number,
                b.site_code,
                b.expiry_date,
                b.current_quantity,
                b.days_to_expiry,
                b.alert_level
            FROM {_SCHEMA}.feat_expiry_alerts b
            {where_clause}
            ORDER BY b.days_to_expiry ASC, b.drug_code
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [ExpiryAlert(**dict(r)) for r in rows]

    def get_expired(self, filters: ExpiryFilter) -> list[ExpiryAlert]:
        """Return all batches past their expiry date."""
        where, params = build_where_eq(
            [
                ("b.site_code", "site_code", filters.site_code),
                ("b.drug_code", "drug_code", filters.drug_code),
            ],
            extra_clauses=["b.days_to_expiry <= 0", "b.current_quantity > 0"],
        )
        where_clause = f"WHERE {where}"
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                b.drug_code,
                b.drug_name,
                b.drug_brand,
                b.batch_number,
                b.site_code,
                b.expiry_date,
                b.current_quantity,
                b.days_to_expiry,
                b.alert_level
            FROM {_SCHEMA}.feat_expiry_alerts b
            {where_clause}
            ORDER BY b.expiry_date ASC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [ExpiryAlert(**dict(r)) for r in rows]

    # ── Summary ────────────────────────────────────────────────────────────

    def get_expiry_summary(self, filters: ExpiryFilter) -> list[ExpirySummary]:
        """Return batch counts by expiry bucket per site from agg_expiry_summary."""
        where, params = build_where_eq([("site_code", "site_code", filters.site_code)])
        where_clause = f"WHERE {where}" if params else ""

        stmt = text(f"""
            SELECT
                site_key,
                site_code,
                site_name,
                expiry_bucket,
                batch_count,
                total_quantity,
                total_value
            FROM {_SCHEMA}.agg_expiry_summary
            {where_clause}
            ORDER BY site_code, expiry_bucket
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [ExpirySummary(**dict(r)) for r in rows]

    # ── Exposure tiers (tenant aggregate, 30/60/90) ────────────────────────

    def get_exposure_tiers(self, filters: ExpiryFilter) -> list[ExpiryExposureTier]:
        """Tenant-aggregate EGP exposure per 30/60/90-day tier.

        Queries ``dim_batch`` directly because ``agg_expiry_summary`` is
        bucketed by ``computed_status`` (active/near_expiry/expired),
        which does not map 1:1 to 30/60/90-day day-bands.

        Always returns exactly three rows — zero-valued tiers included —
        in the order 30d → 60d → 90d. RLS scopes rows to the current
        tenant; no explicit ``tenant_id`` filter is required.
        """
        from decimal import Decimal

        where, params = build_where_eq(
            [("b.site_code", "site_code", filters.site_code)],
            extra_clauses=[
                "b.batch_key != -1",
                "b.current_quantity > 0",
                "b.days_to_expiry > 0",  # exclude already-expired
                "b.days_to_expiry <= 90",
            ],
        )
        where_clause = f"WHERE {where}"

        stmt = text(f"""
            SELECT
                CASE
                    WHEN b.days_to_expiry <= 30 THEN '30d'
                    WHEN b.days_to_expiry <= 60 THEN '60d'
                    ELSE '90d'
                END AS tier,
                COUNT(*)::INT AS batch_count,
                COALESCE(
                    SUM(b.current_quantity * COALESCE(b.unit_cost, 0)),
                    0
                )::NUMERIC(18, 4) AS total_egp
            FROM {_SCHEMA}.dim_batch b
            {where_clause}
            GROUP BY tier
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        values = {
            str(r["tier"]): (int(r["batch_count"]), Decimal(str(r["total_egp"]))) for r in rows
        }

        tiers: list[tuple[str, str, str]] = [
            ("30d", "Within 30 days", "red"),
            ("60d", "31-60 days", "amber"),
            ("90d", "61-90 days", "green"),
        ]
        return [
            ExpiryExposureTier(
                tier=tier,
                label=label,
                total_egp=values.get(tier, (0, Decimal("0")))[1],
                batch_count=values.get(tier, (0, Decimal("0")))[0],
                tone=tone,
            )
            for tier, label, tone in tiers
        ]

    # ── Calendar ───────────────────────────────────────────────────────────

    def get_expiry_calendar(
        self, start_date: date, end_date: date, filters: ExpiryFilter
    ) -> list[ExpiryCalendarDay]:
        """Return day-by-day expiry counts between start_date and end_date."""
        where, params = build_where(
            [
                ("b.expiry_date", ">=", "start_date", start_date),
                ("b.expiry_date", "<=", "end_date", end_date),
                ("b.site_code", "=", "site_code", filters.site_code),
            ],
            extra_clauses=["b.batch_key != -1", "b.current_quantity > 0"],
        )
        where_clause = f"WHERE {where}"
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                b.expiry_date,
                COUNT(*) AS batch_count,
                SUM(b.current_quantity) AS total_quantity,
                CASE
                    WHEN b.expiry_date < CURRENT_DATE         THEN 'expired'
                    WHEN b.expiry_date <= CURRENT_DATE + 30   THEN 'critical'
                    WHEN b.expiry_date <= CURRENT_DATE + 60   THEN 'warning'
                    WHEN b.expiry_date <= CURRENT_DATE + 90   THEN 'caution'
                    ELSE 'safe'
                END AS alert_level
            FROM {_SCHEMA}.dim_batch b
            {where_clause}
            GROUP BY b.expiry_date
            ORDER BY b.expiry_date ASC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [ExpiryCalendarDay(**dict(r)) for r in rows]

    # ── FEFO raw data ──────────────────────────────────────────────────────

    def get_active_batches_for_fefo(self, drug_code: str, site_code: str) -> list[dict]:
        """Return active batches for a drug/site sorted by expiry ascending for FEFO."""
        stmt = text("""
            SELECT
                batch_number,
                expiry_date,
                current_quantity
            FROM public_marts.dim_batch
            WHERE drug_code = :drug_code
              AND site_code = :site_code
              AND batch_key != -1
              AND current_quantity > 0
              AND computed_status NOT IN ('expired', 'quarantined', 'written_off')
            ORDER BY expiry_date ASC
        """)

        rows = (
            self._session.execute(stmt, {"drug_code": drug_code, "site_code": site_code})
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    # ── Write ──────────────────────────────────────────────────────────────

    def quarantine_batch(self, tenant_id: int, request: QuarantineRequest) -> None:
        """Update batch status to 'quarantined' in bronze.batches."""
        now = datetime.now(tz=UTC)
        stmt = text("""
            UPDATE bronze.batches
            SET status = 'quarantined',
                quarantine_date = :now,
                notes = :reason
            WHERE tenant_id = :tenant_id
              AND drug_code = :drug_code
              AND site_code = :site_code
              AND batch_number = :batch_number
        """)

        self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "drug_code": request.drug_code,
                "site_code": request.site_code,
                "batch_number": request.batch_number,
                "reason": request.reason,
                "now": now,
            },
        )

        self._create_stock_adjustment(
            tenant_id=tenant_id,
            drug_code=request.drug_code,
            site_code=request.site_code,
            batch_number=request.batch_number,
            adjustment_type="quarantine",
            quantity=0,
            reason=request.reason,
        )

        log.info(
            "batch_quarantined",
            drug_code=request.drug_code,
            batch_number=request.batch_number,
        )

    def write_off_batch(self, tenant_id: int, request: WriteOffRequest) -> None:
        """Update batch status to 'written_off' in bronze.batches and record write-off."""
        now = datetime.now(tz=UTC)
        stmt = text("""
            UPDATE bronze.batches
            SET status = 'written_off',
                write_off_date = :now,
                write_off_reason = :reason,
                current_quantity = GREATEST(current_quantity - :quantity, 0)
            WHERE tenant_id = :tenant_id
              AND drug_code = :drug_code
              AND site_code = :site_code
              AND batch_number = :batch_number
        """)

        self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "drug_code": request.drug_code,
                "site_code": request.site_code,
                "batch_number": request.batch_number,
                "quantity": float(request.quantity),
                "reason": request.reason,
                "now": now,
            },
        )

        self._create_stock_adjustment(
            tenant_id=tenant_id,
            drug_code=request.drug_code,
            site_code=request.site_code,
            batch_number=request.batch_number,
            adjustment_type="write_off",
            quantity=-float(request.quantity),
            reason=request.reason,
        )

        log.info(
            "batch_written_off",
            drug_code=request.drug_code,
            batch_number=request.batch_number,
            quantity=float(request.quantity),
        )

    def _create_stock_adjustment(
        self,
        *,
        tenant_id: int,
        drug_code: str,
        site_code: str,
        batch_number: str,
        adjustment_type: str,
        quantity: float,
        reason: str,
    ) -> None:
        """Insert a stock adjustment event for audit trail."""
        stmt = text("""
            INSERT INTO bronze.stock_adjustments (
                tenant_id, source_file, adjustment_date,
                adjustment_type, drug_code, site_code,
                batch_number, quantity, reason, loaded_at
            ) VALUES (
                :tenant_id, 'api', :adjustment_date,
                :adjustment_type, :drug_code, :site_code,
                :batch_number, :quantity, :reason, :loaded_at
            )
        """)

        self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "adjustment_date": date.today(),
                "adjustment_type": adjustment_type,
                "drug_code": drug_code,
                "site_code": site_code,
                "batch_number": batch_number,
                "quantity": quantity,
                "reason": reason,
                "loaded_at": datetime.now(tz=UTC),
            },
        )
