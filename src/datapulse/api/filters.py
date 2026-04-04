"""Advanced filter DSL for API endpoints.

Parses URL query parameters in the format ?filter[field][op]=value
into structured filter conditions that can be applied to SQLAlchemy queries.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import Column, and_

from datapulse.logging import get_logger

log = get_logger(__name__)

# Allowed fields for filtering — prevents SQL injection via field names
ALLOWED_FIELDS = frozenset(
    {
        "date",
        "category",
        "brand",
        "site_name",
        "staff_name",
        "customer_name",
        "net_sales",
        "quantity",
        "product_name",
        "billing_type",
        "return_rate",
        "revenue",
        "date_key",
        "year_month",
        "product_key",
        "customer_key",
        "staff_key",
        "site_key",
        "run_type",
        "status",
    }
)

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class FilterOp(StrEnum):
    """Supported filter operators."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    BETWEEN = "between"
    LIKE = "like"
    IS_NULL = "is_null"


class FilterCondition(BaseModel):
    """A single parsed filter condition."""

    field: str
    op: FilterOp
    value: Any

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        if v not in ALLOWED_FIELDS:
            raise ValueError(f"Field '{v}' not allowed for filtering")
        if not _SAFE_IDENTIFIER_RE.match(v):
            raise ValueError(f"Invalid field name: {v}")
        return v


def parse_filters(query_params: dict[str, str]) -> list[FilterCondition]:
    """Parse URL query params into filter conditions.

    Format: ?filter[field][op]=value
    Examples:
        ?filter[net_sales][gte]=10000
        ?filter[category][in]=Pharma,OTC
        ?filter[date][between]=2024-01-01,2024-12-31
        ?filter[brand][like]=aspirin
    """
    filters: list[FilterCondition] = []
    filter_re = re.compile(r"^filter\[([a-z_]+)\]\[([a-z_]+)\]$")

    for key, value in query_params.items():
        match = filter_re.match(key)
        if not match:
            continue
        field_name, op_name = match.groups()
        try:
            op = FilterOp(op_name)
            filters.append(FilterCondition(field=field_name, op=op, value=value))
        except (ValueError, Exception) as exc:
            log.warning("filter_parse_error", key=key, value=value, error=str(exc))

    return filters


def apply_filters(
    query: Any,
    filters: list[FilterCondition],
    column_map: dict[str, Column],
) -> Any:
    """Apply parsed filter conditions to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query or select statement.
        filters: Parsed filter conditions.
        column_map: Mapping of field names to SQLAlchemy Column objects.

    Returns:
        Modified query with WHERE conditions applied.
    """
    conditions = []

    for f in filters:
        col = column_map.get(f.field)
        if col is None:
            continue

        if f.op == FilterOp.EQ:
            conditions.append(col == f.value)
        elif f.op == FilterOp.NEQ:
            conditions.append(col != f.value)
        elif f.op == FilterOp.GT:
            conditions.append(col > f.value)
        elif f.op == FilterOp.GTE:
            conditions.append(col >= f.value)
        elif f.op == FilterOp.LT:
            conditions.append(col < f.value)
        elif f.op == FilterOp.LTE:
            conditions.append(col <= f.value)
        elif f.op == FilterOp.IN:
            values = [v.strip() for v in str(f.value).split(",")]
            conditions.append(col.in_(values))
        elif f.op == FilterOp.BETWEEN:
            parts = str(f.value).split(",", 1)
            if len(parts) == 2:
                low, high = parts[0].strip(), parts[1].strip()
                if not low or not high:
                    log.warning(
                        "filter_between_invalid",
                        field=f.field,
                        value=f.value,
                        reason="both low and high values required",
                    )
                    continue
                # Ensure low <= high to prevent reversed ranges
                if low > high:
                    low, high = high, low
                conditions.append(col.between(low, high))
            else:
                log.warning(
                    "filter_between_invalid",
                    field=f.field,
                    value=f.value,
                    reason="expected two comma-separated values",
                )
        elif f.op == FilterOp.LIKE:
            conditions.append(col.ilike(f"%{f.value}%"))
        elif f.op == FilterOp.IS_NULL:
            if str(f.value).lower() == "true":
                conditions.append(col.is_(None))
            else:
                conditions.append(col.isnot(None))

    if conditions:
        query = query.where(and_(*conditions))

    return query
