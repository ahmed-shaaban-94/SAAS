"""Inventory repository — parameterized SQL queries against the gold layer."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.inventory.models import (
    AdjustmentRequest,
    InventoryCount,
    InventoryFilter,
    ReorderAlert,
    StockLevel,
    StockMovement,
    StockReconciliation,
    StockValuation,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_SCHEMA = "public_marts"


class InventoryRepository:
    """Read (and limited write) access to inventory gold-layer tables.

    All SQL uses parameterized queries via SQLAlchemy ``text()``.
    No f-string SQL — column names are never interpolated.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Stock Levels ──────────────────────────────────────────────────────

    def get_stock_levels(self, filters: InventoryFilter) -> list[StockLevel]:
        """Return current stock levels, optionally filtered by site or drug."""
        params: dict = {}
        wheres: list[str] = []

        if filters.site_key is not None:
            wheres.append("site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.drug_code is not None:
            wheres.append("drug_code = :drug_code")
            params["drug_code"] = filters.drug_code

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, drug_code, drug_name, drug_brand,
                site_key, site_code, site_name,
                current_quantity, total_received, total_dispensed,
                total_wastage, last_movement_date
            FROM {_SCHEMA}.agg_stock_levels
            {where_clause}
            ORDER BY drug_name, site_code
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [StockLevel(**dict(r)) for r in rows]

    def get_stock_level_by_drug(self, drug_code: str, filters: InventoryFilter) -> list[StockLevel]:
        """Return stock levels for a specific drug across all sites."""
        params: dict = {"drug_code": drug_code, "limit": filters.limit}
        wheres = ["drug_code = :drug_code"]

        if filters.site_key is not None:
            wheres.append("site_key = :site_key")
            params["site_key"] = filters.site_key

        where_clause = f"WHERE {' AND '.join(wheres)}"
        stmt = text(f"""
            SELECT
                product_key, drug_code, drug_name, drug_brand,
                site_key, site_code, site_name,
                current_quantity, total_received, total_dispensed,
                total_wastage, last_movement_date
            FROM {_SCHEMA}.agg_stock_levels
            {where_clause}
            ORDER BY site_code
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [StockLevel(**dict(r)) for r in rows]

    # ── Movements ─────────────────────────────────────────────────────────

    def get_movements(self, filters: InventoryFilter) -> list[StockMovement]:
        """Return movement events with product/site names, filtered by provided criteria."""
        params: dict = {}
        wheres: list[str] = []

        if filters.site_key is not None:
            wheres.append("m.site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.drug_code is not None:
            wheres.append("p.drug_code = :drug_code")
            params["drug_code"] = filters.drug_code
        if filters.movement_type is not None:
            wheres.append("m.movement_type = :movement_type")
            params["movement_type"] = filters.movement_type
        if filters.start_date is not None:
            wheres.append("m.movement_date >= :start_date")
            params["start_date"] = filters.start_date
        if filters.end_date is not None:
            wheres.append("m.movement_date <= :end_date")
            params["end_date"] = filters.end_date

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                m.movement_key,
                m.movement_date,
                m.movement_type,
                COALESCE(p.drug_code, '')   AS drug_code,
                COALESCE(p.drug_name, '')   AS drug_name,
                COALESCE(s.site_code, '')   AS site_code,
                m.batch_number,
                m.quantity,
                m.unit_cost,
                m.reference
            FROM {_SCHEMA}.fct_stock_movements m
            LEFT JOIN public_marts.dim_product p
                ON m.product_key = p.product_key AND m.tenant_id = p.tenant_id
            LEFT JOIN public_marts.dim_site s
                ON m.site_key = s.site_key AND m.tenant_id = s.tenant_id
            {where_clause}
            ORDER BY m.movement_date DESC, m.movement_key
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [StockMovement(**dict(r)) for r in rows]

    def get_movements_by_drug(
        self, drug_code: str, filters: InventoryFilter
    ) -> list[StockMovement]:
        """Return all movements for a specific drug."""
        updated = InventoryFilter(**{**filters.model_dump(), "drug_code": drug_code})
        return self.get_movements(updated)

    # ── Valuation ─────────────────────────────────────────────────────────

    def get_valuation(self, filters: InventoryFilter) -> list[StockValuation]:
        """Return stock valuation (WAC) per product/site."""
        params: dict = {}
        wheres: list[str] = []

        if filters.site_key is not None:
            wheres.append("site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.drug_code is not None:
            wheres.append("drug_code = :drug_code")
            params["drug_code"] = filters.drug_code

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, drug_code, drug_name,
                site_key, site_code,
                weighted_avg_cost, current_quantity, stock_value
            FROM {_SCHEMA}.agg_stock_valuation
            {where_clause}
            ORDER BY stock_value DESC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [StockValuation(**dict(r)) for r in rows]

    def get_valuation_by_drug(
        self, drug_code: str, filters: InventoryFilter
    ) -> list[StockValuation]:
        """Return valuation for a specific drug."""
        updated = InventoryFilter(**{**filters.model_dump(), "drug_code": drug_code})
        return self.get_valuation(updated)

    # ── Reorder Alerts ────────────────────────────────────────────────────

    def get_reorder_alerts(self, filters: InventoryFilter) -> list[ReorderAlert]:
        """Return products where current_quantity <= reorder_point.

        Enriches each row with a trailing-30-day sales velocity and a
        derived ``status`` tier (#507). The velocity CTE uses
        ``fct_sales`` scoped to the current tenant via RLS; the LEFT JOIN
        ensures items with zero recent sales still surface.
        """

        params: dict = {}
        wheres = ["sl.current_quantity <= rc.reorder_point"]

        if filters.site_key is not None:
            wheres.append("sl.site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.drug_code is not None:
            wheres.append("sl.drug_code = :drug_code")
            params["drug_code"] = filters.drug_code

        where_clause = f"WHERE {' AND '.join(wheres)}"
        params["limit"] = filters.limit

        stmt = text(f"""
            WITH velocity AS (
                SELECT
                    p.drug_code,
                    f.site_key,
                    ROUND(
                        SUM(f.quantity) FILTER (WHERE NOT f.is_return) / 30.0,
                        4
                    ) AS daily_velocity
                FROM {_SCHEMA}.fct_sales f
                INNER JOIN {_SCHEMA}.dim_product p
                    ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
                WHERE f.date_key >= TO_CHAR(
                    CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD'
                )::INT
                GROUP BY p.drug_code, f.site_key
            )
            SELECT
                sl.product_key,
                sl.site_key,
                sl.drug_code,
                sl.drug_name,
                sl.site_code,
                sl.current_quantity,
                rc.reorder_point,
                rc.reorder_quantity,
                COALESCE(v.daily_velocity, 0) AS daily_velocity
            FROM {_SCHEMA}.agg_stock_levels sl
            INNER JOIN public.reorder_config rc
                ON sl.drug_code = rc.drug_code
               AND sl.site_code = rc.site_code
               AND sl.tenant_id = rc.tenant_id
            LEFT JOIN velocity v
                ON v.drug_code = sl.drug_code
               AND v.site_key = sl.site_key
            {where_clause}
            ORDER BY (sl.current_quantity - rc.reorder_point) ASC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [self._row_to_reorder_alert(dict(r)) for r in rows]

    @staticmethod
    def _row_to_reorder_alert(row: dict) -> ReorderAlert:
        """Compute derived ``days_of_stock`` + ``status`` from a raw row.

        Kept dependency-free (pure function) so the threshold logic is
        easy to unit-test without the DB in the loop.
        """
        current = Decimal(str(row["current_quantity"]))
        velocity = Decimal(str(row.get("daily_velocity", 0) or 0))

        days_of_stock = (current / velocity).quantize(Decimal("0.1")) if velocity > 0 else None

        if days_of_stock is None:
            # No recent sales → don't claim "critical" or "healthy"; the
            # item is below its reorder point so "low" is the honest default.
            status = "low"
        elif days_of_stock < Decimal("5"):
            status = "critical"
        elif days_of_stock < Decimal("10"):
            status = "low"
        else:
            status = "healthy"

        return ReorderAlert(
            product_key=row["product_key"],
            site_key=row["site_key"],
            drug_code=row["drug_code"],
            drug_name=row["drug_name"],
            site_code=row["site_code"],
            current_quantity=current,
            reorder_point=row["reorder_point"],
            reorder_quantity=row["reorder_quantity"],
            daily_velocity=velocity,
            days_of_stock=days_of_stock,
            status=status,
        )

    # ── Physical Counts ───────────────────────────────────────────────────

    def get_counts(self, filters: InventoryFilter) -> list[InventoryCount]:
        """Return physical inventory count records."""
        params: dict = {}
        wheres: list[str] = []

        if filters.site_key is not None:
            wheres.append("site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.drug_code is not None:
            wheres.append("p.drug_code = :drug_code")
            params["drug_code"] = filters.drug_code
        if filters.start_date is not None:
            wheres.append("count_date >= :start_date")
            params["start_date"] = filters.start_date
        if filters.end_date is not None:
            wheres.append("count_date <= :end_date")
            params["end_date"] = filters.end_date

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                c.count_key,
                c.tenant_id,
                c.product_key,
                c.site_key,
                c.count_date,
                p.drug_code,
                s.site_code,
                c.batch_number,
                c.counted_quantity,
                c.counted_by
            FROM {_SCHEMA}.fct_inventory_counts c
            LEFT JOIN public_marts.dim_product p
                ON c.product_key = p.product_key AND c.tenant_id = p.tenant_id
            LEFT JOIN public_marts.dim_site s
                ON c.site_key = s.site_key AND c.tenant_id = s.tenant_id
            {where_clause}
            ORDER BY c.count_date DESC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [InventoryCount(**dict(r)) for r in rows]

    # ── Reconciliation ────────────────────────────────────────────────────

    def get_reconciliation(self, filters: InventoryFilter) -> list[StockReconciliation]:
        """Return reconciliation report (counted vs calculated)."""
        params: dict = {}
        wheres: list[str] = []

        if filters.site_key is not None:
            wheres.append("site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.drug_code is not None:
            wheres.append("drug_code = :drug_code")
            params["drug_code"] = filters.drug_code
        if filters.start_date is not None:
            wheres.append("count_date >= :start_date")
            params["start_date"] = filters.start_date
        if filters.end_date is not None:
            wheres.append("count_date <= :end_date")
            params["end_date"] = filters.end_date

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, site_key, count_date,
                drug_code, drug_name, site_code, site_name,
                counted_quantity, calculated_quantity,
                variance, variance_pct
            FROM {_SCHEMA}.agg_stock_reconciliation
            {where_clause}
            ORDER BY ABS(variance) DESC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [StockReconciliation(**dict(r)) for r in rows]

    # ── Write ─────────────────────────────────────────────────────────────

    def create_adjustment(self, tenant_id: int, request: AdjustmentRequest) -> None:
        """Insert a manual adjustment record into bronze.stock_adjustments.

        The record will be picked up by dbt staging on the next pipeline run.
        """
        stmt = text("""
            INSERT INTO bronze.stock_adjustments (
                tenant_id,
                source_file,
                adjustment_date,
                adjustment_type,
                drug_code,
                site_code,
                batch_number,
                quantity,
                reason,
                loaded_at
            ) VALUES (
                :tenant_id,
                :source_file,
                :adjustment_date,
                :adjustment_type,
                :drug_code,
                :site_code,
                :batch_number,
                :quantity,
                :reason,
                :loaded_at
            )
        """)

        self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "source_file": "api",
                "adjustment_date": date.today(),
                "adjustment_type": request.adjustment_type,
                "drug_code": request.drug_code,
                "site_code": request.site_code,
                "batch_number": request.batch_number,
                "quantity": float(request.quantity),
                "reason": request.reason,
                "loaded_at": datetime.now(tz=UTC),
            },
        )
        log.info(
            "adjustment_created",
            drug_code=request.drug_code,
            site_code=request.site_code,
            adjustment_type=request.adjustment_type,
            quantity=float(request.quantity),
        )
