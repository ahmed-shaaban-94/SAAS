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
        "drug_name",
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
    ) -> dict[int, tuple[str, Decimal]]:
        """Return {key: (name, total_net_amount)} for top entities."""
        where, params = build_where(filters, use_year_month=True)
        params["limit"] = limit

        stmt = text(f"""
            SELECT {key_col}, {name_col}, SUM(total_net_amount) AS value
            FROM {table}
            WHERE {where}
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

        # Fetch broader set to find movers (top 50 from each period)
        fetch_limit = max(limit * 10, 50)
        current = self._fetch_period_totals(table, key_col, name_col, current_filters, fetch_limit)
        previous = self._fetch_period_totals(
            table, key_col, name_col, previous_filters, fetch_limit
        )

        movers: list[MoverItem] = []
        all_keys = set(current) | set(previous)

        for key in all_keys:
            curr_name, curr_val = current.get(key, ("", _ZERO))
            prev_name, prev_val = previous.get(key, ("", _ZERO))
            name = curr_name or prev_name

            if prev_val == _ZERO and curr_val == _ZERO:
                continue

            change = safe_growth(curr_val, prev_val)
            if change is None:
                # New entity (not in previous) — treat as +100%
                change = Decimal("100.00")

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
