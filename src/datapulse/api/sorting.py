"""Multi-field sorting for API endpoints.

Parses a sort parameter (e.g., ?sort=net_sales:desc,name:asc)
into SQLAlchemy ORDER BY clauses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Column, asc, desc

from datapulse.logging import get_logger

log = get_logger(__name__)

# Allowed sort fields — prevents SQL injection
ALLOWED_SORT_FIELDS = frozenset({
    "date", "date_key", "net_sales", "quantity", "revenue",
    "name", "product_name", "customer_name", "staff_name", "site_name",
    "rank", "key", "pct_of_total", "return_rate", "return_quantity",
    "started_at", "finished_at", "duration_seconds", "rows_loaded",
    "status", "year_month",
})

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class SortField:
    """A parsed sort directive."""

    field: str
    direction: str  # "asc" or "desc"


def parse_sort(sort_param: str | None) -> list[SortField]:
    """Parse a sort parameter string into SortField objects.

    Format: ?sort=field1:desc,field2:asc
    Default direction is asc if not specified.
    """
    if not sort_param:
        return []

    fields: list[SortField] = []
    for part in sort_param.split(","):
        part = part.strip()
        if not part:
            continue

        if ":" in part:
            field_name, direction = part.rsplit(":", 1)
            direction = direction.lower()
            if direction not in ("asc", "desc"):
                direction = "asc"
        else:
            field_name = part
            direction = "asc"

        field_name = field_name.strip()
        if field_name in ALLOWED_SORT_FIELDS and _SAFE_IDENTIFIER_RE.match(field_name):
            fields.append(SortField(field=field_name, direction=direction))
        else:
            log.warning("sort_field_rejected", field=field_name)

    return fields


def apply_sort(
    query: Any,
    sort_fields: list[SortField],
    column_map: dict[str, Column],
) -> Any:
    """Apply multi-field sorting to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query or select statement.
        sort_fields: Parsed sort directives.
        column_map: Mapping of field names to SQLAlchemy Column objects.

    Returns:
        Modified query with ORDER BY clauses applied.
    """
    for sf in sort_fields:
        col = column_map.get(sf.field)
        if col is None:
            continue
        order_fn = desc if sf.direction == "desc" else asc
        query = query.order_by(order_fn(col))

    return query
