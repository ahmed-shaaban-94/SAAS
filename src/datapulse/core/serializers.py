"""Shared serialization utilities for converting DB values to JSON-safe types."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def serialise_value(value: Any) -> str | int | float | bool | None:
    """Convert a DB value to a JSON-safe primitive.

    Used by the async query executor, embed endpoint, and report template engine
    to normalize SQLAlchemy result values before JSON serialization.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)
