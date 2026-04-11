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
    except Exception as exc:
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


def _extract_cursor_value(item: Any, cursor_field: str) -> Any:
    """Extract the cursor field value from an item (object or dict)."""
    if hasattr(item, cursor_field):
        return getattr(item, cursor_field, None)
    if isinstance(item, dict):
        return item.get(cursor_field)
    return None


def build_cursor_page(
    items: list[Any],
    limit: int,
    cursor_field: str = "key",
    total_count: int | None = None,
    has_prev: bool = False,
    current_cursor: str | None = None,
) -> CursorPage:
    """Build a CursorPage from a list of items.

    The items list should contain `limit + 1` items if there are more
    results. The extra item is used to determine `has_next` and is
    removed from the response.

    When *current_cursor* is provided (i.e. not the first page), a
    *prev_cursor* is generated from the first item in the page so
    callers can navigate backward.
    """
    has_next = len(items) > limit
    page_items = items[:limit]

    next_cursor = None
    if has_next and page_items:
        cursor_val = _extract_cursor_value(page_items[-1], cursor_field)
        if cursor_val is not None:
            next_cursor = encode_cursor({cursor_field: cursor_val})

    prev_cursor = None
    if current_cursor is not None and page_items:
        cursor_val = _extract_cursor_value(page_items[0], cursor_field)
        if cursor_val is not None:
            prev_cursor = encode_cursor({cursor_field: cursor_val, "__dir": "prev"})

    return CursorPage(
        items=page_items,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        has_next=has_next,
        has_prev=current_cursor is not None or has_prev,
        total_count=total_count,
    )
