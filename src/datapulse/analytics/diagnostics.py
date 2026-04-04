"""Diagnostics repository — Why Engine for revenue decomposition.

Decomposes period-over-period revenue changes into dimension-level drivers
(product, customer, staff, site) using FULL OUTER JOIN comparisons.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    RevenueDriver,
    WaterfallAnalysis,
)
from datapulse.analytics.queries import build_where, safe_growth
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")

# Dimension configs: (table, key_col, name_col)
_DIMENSIONS: dict[str, tuple[str, str, str]] = {
    "product": ("public_marts.agg_sales_by_product", "product_key", "drug_name"),
    "customer": ("public_marts.agg_sales_by_customer", "customer_key", "customer_name"),
    "staff": ("public_marts.agg_sales_by_staff", "staff_key", "staff_name"),
    "site": ("public_marts.agg_sales_by_site", "site_key", "site_name"),
}


class DiagnosticsRepository:
    """Period-over-period revenue decomposition by dimension."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_revenue_drivers(
        self,
        current_filters: AnalyticsFilter,
        previous_filters: AnalyticsFilter,
        *,
        limit: int = 15,
    ) -> WaterfallAnalysis:
        """Decompose revenue change across all dimensions.

        For each dimension, compares current vs previous period totals,
        calculates impact per entity, and merges into a sorted list.
        """
        log.info(
            "get_revenue_drivers",
            current=current_filters.model_dump(),
            previous=previous_filters.model_dump(),
        )

        all_drivers: list[RevenueDriver] = []
        current_total = _ZERO
        previous_total = _ZERO

        for dim_name, (table, key_col, name_col) in _DIMENSIONS.items():
            drivers, c_total, p_total = self._decompose_dimension(
                dim_name,
                table,
                key_col,
                name_col,
                current_filters,
                previous_filters,
            )
            all_drivers.extend(drivers)
            # Use max total across dimensions (they should be similar)
            if c_total > current_total:
                current_total = c_total
            if p_total > previous_total:
                previous_total = p_total

        total_change = current_total - previous_total
        total_change_pct = safe_growth(current_total, previous_total)

        # Sort by absolute impact, take top N
        all_drivers.sort(key=lambda d: abs(d.impact), reverse=True)
        top_drivers = all_drivers[:limit]

        # Calculate impact_pct relative to total change
        if total_change != _ZERO:
            top_drivers = [
                RevenueDriver(
                    dimension=d.dimension,
                    entity_key=d.entity_key,
                    entity_name=d.entity_name,
                    current_value=d.current_value,
                    previous_value=d.previous_value,
                    impact=d.impact,
                    impact_pct=(d.impact / total_change * 100).quantize(Decimal("0.01")),
                    direction=d.direction,
                )
                for d in top_drivers
            ]

        # Unexplained = total change - sum of top driver impacts
        explained = sum((d.impact for d in top_drivers), _ZERO)
        unexplained = total_change - explained

        return WaterfallAnalysis(
            current_total=current_total,
            previous_total=previous_total,
            total_change=total_change,
            total_change_pct=total_change_pct,
            drivers=top_drivers,
            unexplained=unexplained,
        )

    def _decompose_dimension(
        self,
        dim_name: str,
        table: str,
        key_col: str,
        name_col: str,
        current_filters: AnalyticsFilter,
        previous_filters: AnalyticsFilter,
    ) -> tuple[list[RevenueDriver], Decimal, Decimal]:
        """Compare a single dimension between two periods via FULL OUTER JOIN."""
        c_where, c_params = build_where(current_filters, use_year_month=True)
        p_where, p_params = build_where(previous_filters, use_year_month=True)

        # Prefix params to avoid collisions
        c_params_prefixed = {f"c_{k}": v for k, v in c_params.items()}
        p_params_prefixed = {f"p_{k}": v for k, v in p_params.items()}

        c_where_prefixed = c_where
        p_where_prefixed = p_where
        for key in c_params:
            c_where_prefixed = c_where_prefixed.replace(f":{key}", f":c_{key}")
        for key in p_params:
            p_where_prefixed = p_where_prefixed.replace(f":{key}", f":p_{key}")

        stmt = text(f"""
            WITH current_period AS (
                SELECT {key_col}, {name_col}, SUM(total_net_amount) AS net
                FROM {table}
                WHERE {c_where_prefixed}
                GROUP BY {key_col}, {name_col}
            ),
            previous_period AS (
                SELECT {key_col}, {name_col}, SUM(total_net_amount) AS net
                FROM {table}
                WHERE {p_where_prefixed}
                GROUP BY {key_col}, {name_col}
            )
            SELECT
                COALESCE(c.{key_col}, p.{key_col}) AS entity_key,
                COALESCE(c.{name_col}, p.{name_col}) AS entity_name,
                COALESCE(c.net, 0) AS current_value,
                COALESCE(p.net, 0) AS previous_value,
                COALESCE(c.net, 0) - COALESCE(p.net, 0) AS impact
            FROM current_period c
            FULL OUTER JOIN previous_period p ON c.{key_col} = p.{key_col}
            WHERE COALESCE(c.net, 0) - COALESCE(p.net, 0) != 0
            ORDER BY ABS(COALESCE(c.net, 0) - COALESCE(p.net, 0)) DESC
            LIMIT 20
        """)

        all_params = {**c_params_prefixed, **p_params_prefixed}
        rows = self._session.execute(stmt, all_params).fetchall()

        # Also get totals for this dimension
        c_total_stmt = text(f"""
            SELECT COALESCE(SUM(total_net_amount), 0)
            FROM {table} WHERE {c_where_prefixed}
        """)
        p_total_stmt = text(f"""
            SELECT COALESCE(SUM(total_net_amount), 0)
            FROM {table} WHERE {p_where_prefixed}
        """)
        c_total = Decimal(str(self._session.execute(c_total_stmt, c_params_prefixed).scalar() or 0))
        p_total = Decimal(str(self._session.execute(p_total_stmt, p_params_prefixed).scalar() or 0))

        drivers = [
            RevenueDriver(
                dimension=dim_name,
                entity_key=int(r[0]),
                entity_name=str(r[1]),
                current_value=Decimal(str(r[2])),
                previous_value=Decimal(str(r[3])),
                impact=Decimal(str(r[4])),
                impact_pct=_ZERO,  # calculated later
                direction="positive" if Decimal(str(r[4])) > _ZERO else "negative",
            )
            for r in rows
        ]

        return drivers, c_total, p_total
