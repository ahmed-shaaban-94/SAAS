"""Repository for period-over-period comparison queries.

Powers the "Top Movers" feature — identifies products, customers, or staff
with the biggest growth or decline between two time periods.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    MoverItem,
    TopMovers,
)
from datapulse.analytics.queries import (
    build_where,
    safe_growth,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")

# Map entity_type -> (table, key_col, name_col)
_ENTITY_MAP: dict[str, tuple[str, str, str]] = {
    "product": (
        "public_marts.agg_sales_by_product",
        "product_key",
        "drug_brand",
    ),
    "customer": (
        "public_marts.agg_sales_by_customer",
        "customer_key",
        "customer_name",
    ),
    "staff": (
        "public_marts.agg_sales_by_staff",
        "staff_key",
        "staff_name",
    ),
}


class ComparisonRepository:
    """Period-over-period comparison queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _fetch_period_totals(
        self,
        table: str,
        key_col: str,
        name_col: str,
        filters: AnalyticsFilter,
        limit: int,
        *,
        active_only: bool = False,
    ) -> dict[int, tuple[str, Decimal]]:
        """Return {key: (name, total_sales)} for top entities.

        When *active_only* is True (used for staff), excludes entities with
        transaction counts below 33% of the average — same threshold used
        by get_top_staff in the main repository.
        """
        where, params = build_where(filters, use_year_month=True)
        params["limit"] = limit

        if active_only:
            # Use the fct_sales-based active filter: exclude Unknown, Services/Other,
            # returns, and staff below 33% of average transaction count
            stmt = text(f"""
                WITH staff_txns AS (
                    SELECT f.staff_key,
                           COUNT(*) FILTER (WHERE NOT f.is_return) AS sale_count
                    FROM public_marts.fct_sales f
                    INNER JOIN public_marts.dim_date d ON f.date_key = d.date_key
                    INNER JOIN public_marts.dim_product p ON f.product_key = p.product_key
                        AND f.tenant_id = p.tenant_id
                    WHERE {where}
                      AND f.staff_key != -1
                      AND COALESCE(p.origin, 'Other') IN ('Pharma', 'Non-pharma', 'HVI')
                      AND NOT f.is_return
                    GROUP BY f.staff_key
                ),
                threshold AS (
                    SELECT COALESCE(AVG(sale_count) * 0.33, 0) AS min_txns FROM staff_txns
                ),
                active_staff AS (
                    SELECT staff_key FROM staff_txns, threshold
                    WHERE sale_count >= min_txns
                )
                SELECT a.{key_col}, a.{name_col}, SUM(a.total_sales) AS value
                FROM {table} a
                INNER JOIN active_staff act ON a.{key_col} = act.staff_key
                WHERE {where} AND a.{key_col} != -1
                GROUP BY a.{key_col}, a.{name_col}
                ORDER BY value DESC
                LIMIT :limit
            """)
        else:
            stmt = text(f"""
                SELECT {key_col}, {name_col}, SUM(total_sales) AS value
                FROM {table}
                WHERE {where} AND {key_col} != -1
                GROUP BY {key_col}, {name_col}
                ORDER BY value DESC
                LIMIT :limit
            """)
        rows = self._session.execute(stmt, params).fetchall()
        return {int(r[0]): (str(r[1]), Decimal(str(r[2]))) for r in rows}

    def get_top_movers(
        self,
        entity_type: str,
        current_filters: AnalyticsFilter,
        previous_filters: AnalyticsFilter,
        limit: int = 5,
    ) -> TopMovers:
        """Identify top gainers and losers between two periods."""
        log.info(
            "get_top_movers",
            entity_type=entity_type,
            current=current_filters.model_dump(),
            previous=previous_filters.model_dump(),
        )

        if entity_type not in _ENTITY_MAP:
            raise ValueError(
                f"Invalid entity_type: {entity_type}. Must be one of: {', '.join(_ENTITY_MAP)}"
            )

        table, key_col, name_col = _ENTITY_MAP[entity_type]

        # Fetch broader set to find movers — need enough to catch big swings
        fetch_limit = max(limit * 20, 100)
        is_staff = entity_type == "staff"
        current = self._fetch_period_totals(
            table, key_col, name_col, current_filters, fetch_limit, active_only=is_staff,
        )
        previous = self._fetch_period_totals(
            table, key_col, name_col, previous_filters, fetch_limit, active_only=is_staff,
        )

        movers: list[MoverItem] = []
        all_keys = set(current) | set(previous)

        for key in all_keys:
            curr_name, curr_val = current.get(key, ("", _ZERO))
            prev_name, prev_val = previous.get(key, ("", _ZERO))
            name = curr_name or prev_name

            if prev_val == _ZERO and curr_val == _ZERO:
                continue

            # Compute growth percentage
            if prev_val == _ZERO:
                # New entrant (didn't exist in previous period) — treat as +100%
                change = Decimal("100")
            elif curr_val == _ZERO:
                # Disappeared (existed before, gone now) — treat as -100%
                change = Decimal("-100")
            else:
                change = safe_growth(curr_val, prev_val)
                if change is None:
                    continue

            movers.append(
                MoverItem(
                    key=key,
                    name=name,
                    current_value=curr_val,
                    previous_value=prev_val,
                    change_pct=change,
                    direction="up" if change >= 0 else "down",
                )
            )

        # Sort: gainers by highest positive change, losers by most negative
        gainers = sorted(
            [m for m in movers if m.direction == "up"],
            key=lambda m: m.change_pct,
            reverse=True,
        )[:limit]

        losers = sorted(
            [m for m in movers if m.direction == "down"],
            key=lambda m: m.change_pct,
        )[:limit]

        return TopMovers(
            gainers=gainers,
            losers=losers,
            entity_type=entity_type,
        )
