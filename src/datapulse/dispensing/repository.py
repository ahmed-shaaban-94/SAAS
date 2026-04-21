"""Dispensing analytics repository — parameterized SQL queries against gold feature tables."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.core.sql import build_where_eq
from datapulse.dispensing.models import (
    DaysOfStock,
    DispenseRate,
    DispensingFilter,
    StockoutRisk,
    VelocityClassification,
)
from datapulse.inventory.models import StockReconciliation
from datapulse.logging import get_logger

log = get_logger(__name__)

_SCHEMA = "public_marts"


class DispensingRepository:
    """Read-only access to dispensing analytics feature tables.

    All SQL uses parameterized queries via SQLAlchemy ``text()``.
    No f-string SQL — column names are never interpolated.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Dispense Rates ────────────────────────────────────────────────────────

    def get_dispense_rates(self, filters: DispensingFilter) -> list[DispenseRate]:
        """Return avg dispense rate per product/site over last 90 days."""
        where, params = build_where_eq(
            [
                ("site_key", "site_key", filters.site_key),
                ("drug_code", "drug_code", filters.drug_code),
            ]
        )
        where_clause = f"WHERE {where}" if params else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, site_key, drug_code, drug_name, drug_brand,
                site_code, site_name, active_days, total_dispensed_90d,
                avg_daily_dispense, avg_weekly_dispense, avg_monthly_dispense,
                last_dispense_date_key
            FROM {_SCHEMA}.feat_dispense_rate
            {where_clause}
            ORDER BY avg_daily_dispense DESC NULLS LAST, drug_name
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [DispenseRate(**dict(r)) for r in rows]

    # ── Days of Stock ─────────────────────────────────────────────────────────

    def get_days_of_stock(self, filters: DispensingFilter) -> list[DaysOfStock]:
        """Return days of stock remaining per product/site."""
        where, params = build_where_eq(
            [
                ("site_key", "site_key", filters.site_key),
                ("drug_code", "drug_code", filters.drug_code),
            ]
        )
        where_clause = f"WHERE {where}" if params else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, site_key, drug_code, drug_name,
                site_code, site_name, current_quantity,
                avg_daily_dispense, days_of_stock,
                avg_weekly_dispense, avg_monthly_dispense,
                last_dispense_date_key
            FROM {_SCHEMA}.feat_days_of_stock
            {where_clause}
            ORDER BY days_of_stock ASC NULLS LAST, drug_name
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [DaysOfStock(**dict(r)) for r in rows]

    # ── Product Velocity ──────────────────────────────────────────────────────

    def get_velocity(self, filters: DispensingFilter) -> list[VelocityClassification]:
        """Return product velocity classifications (fast/normal/slow/dead)."""
        where, params = build_where_eq(
            [
                ("drug_code", "drug_code", filters.drug_code),
                ("velocity_class", "velocity_class", filters.velocity_class),
            ]
        )
        where_clause = f"WHERE {where}" if params else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, drug_code, drug_name, drug_brand,
                drug_category, lifecycle_phase, velocity_class,
                avg_daily_dispense, category_avg_daily
            FROM {_SCHEMA}.feat_product_velocity
            {where_clause}
            ORDER BY
                CASE velocity_class
                    WHEN 'fast_mover'   THEN 1
                    WHEN 'normal_mover' THEN 2
                    WHEN 'slow_mover'   THEN 3
                    ELSE 4
                END,
                avg_daily_dispense DESC NULLS LAST
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [VelocityClassification(**dict(r)) for r in rows]

    # ── Stockout Risk ─────────────────────────────────────────────────────────

    def get_stockout_risk(self, filters: DispensingFilter) -> list[StockoutRisk]:
        """Return products at risk of stockout, optionally filtered by risk level."""
        where, params = build_where_eq(
            [
                ("site_key", "site_key", filters.site_key),
                ("drug_code", "drug_code", filters.drug_code),
                ("risk_level", "risk_level", filters.risk_level),
            ]
        )
        where_clause = f"WHERE {where}" if params else ""
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                product_key, site_key, drug_code, drug_name,
                site_code, site_name, current_quantity, days_of_stock,
                avg_daily_dispense, reorder_point, reorder_lead_days,
                min_stock, risk_level, suggested_reorder_qty
            FROM {_SCHEMA}.feat_stockout_risk
            {where_clause}
            ORDER BY
                CASE risk_level
                    WHEN 'stockout'  THEN 1
                    WHEN 'critical'  THEN 2
                    WHEN 'at_risk'   THEN 3
                    ELSE 4
                END,
                current_quantity ASC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [StockoutRisk(**dict(r)) for r in rows]

    # ── Reconciliation ────────────────────────────────────────────────────────

    def get_reconciliation(self, filters: DispensingFilter) -> list[StockReconciliation]:
        """Return stock reconciliation (physical count vs calculated) ordered by variance."""
        where, params = build_where_eq(
            [
                ("site_key", "site_key", filters.site_key),
                ("drug_code", "drug_code", filters.drug_code),
            ]
        )
        where_clause = f"WHERE {where}" if params else ""
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
