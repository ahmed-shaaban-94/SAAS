"""Cursor-based pagination for API endpoints.

Uses keyset pagination (WHERE + ORDER BY) for O(1) performance
regardless of page depth, unlike OFFSET which is O(n).
"""

from __future__ import annotations

import base64
import json
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


def encode_cursor(values: dict[str, Any]) -> str:
    """Encode sort key values into an opaque, URL-safe cursor string."""
    payload = json.dumps(values, default=str, sort_keys=True)
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode an opaque cursor string back to sort key values.

    Raises ValueError if the cursor is malformed.
    """
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(payload)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid cursor: {exc}") from exc


class CursorPage(BaseModel, Generic[T]):
    """Standardized paginated response with cursor-based navigation."""

    model_config = ConfigDict(frozen=True)

    items: list[T]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool
    has_prev: bool
    total_count: int | None = None


def build_cursor_page(
    items: list[Any],
    limit: int,
    cursor_field: str = "key",
    total_count: int | None = None,
    has_prev: bool = False,
) -> CursorPage:
    """Build a CursorPage from a list of items.

    The items list should contain `limit + 1` items if there are more
    results. The extra item is used to determine `has_next` and is
    removed from the response.
    """
    has_next = len(items) > limit
    page_items = items[:limit]

    next_cursor = None
    if has_next and page_items:
        last = page_items[-1]
        cursor_val = getattr(last, cursor_field, None) if hasattr(last, cursor_field) else None
        if cursor_val is None and isinstance(last, dict):
            cursor_val = last.get(cursor_field)
        if cursor_val is not None:
            next_cursor = encode_cursor({cursor_field: cursor_val})

    return CursorPage(
        items=page_items,
        next_cursor=next_cursor,
        prev_cursor=None,
        has_next=has_next,
        has_prev=has_prev,
        total_count=total_count,
    )
