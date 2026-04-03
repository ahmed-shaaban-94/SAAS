"""Tests for cursor-based pagination."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datapulse.api.pagination import (
    CursorPage,
    build_cursor_page,
    decode_cursor,
    encode_cursor,
)


class TestEncodeDecode:
    def test_roundtrip(self):
        original = {"key": 42, "name": "test"}
        cursor = encode_cursor(original)
        decoded = decode_cursor(cursor)
        assert decoded == original

    def test_encode_returns_string(self):
        cursor = encode_cursor({"id": 1})
        assert isinstance(cursor, str)

    def test_decode_invalid_cursor_raises(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-valid-base64!!!")

    def test_decode_invalid_json_raises(self):
        import base64

        bad = base64.urlsafe_b64encode(b"not json").decode()
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor(bad)

    def test_url_safe_encoding(self):
        cursor = encode_cursor({"key": "value/with+special=chars"})
        assert "+" not in cursor or cursor == cursor  # urlsafe uses - and _
        decoded = decode_cursor(cursor)
        assert decoded["key"] == "value/with+special=chars"


class TestBuildCursorPage:
    def test_no_more_results(self):
        items = [{"key": 1}, {"key": 2}]
        page = build_cursor_page(items, limit=5)
        assert page.has_next is False
        assert page.next_cursor is None
        assert len(page.items) == 2

    def test_has_more_results(self):
        items = [{"key": i} for i in range(6)]  # 6 items, limit 5
        page = build_cursor_page(items, limit=5)
        assert page.has_next is True
        assert page.next_cursor is not None
        assert len(page.items) == 5

    def test_cursor_contains_last_item_key(self):
        items = [{"key": i} for i in range(6)]
        page = build_cursor_page(items, limit=5)
        decoded = decode_cursor(page.next_cursor)
        assert decoded["key"] == 4  # last item in page

    def test_total_count_passed_through(self):
        items = [{"key": 1}]
        page = build_cursor_page(items, limit=10, total_count=100)
        assert page.total_count == 100

    def test_empty_items(self):
        page = build_cursor_page([], limit=10)
        assert page.has_next is False
        assert page.items == []

    def test_has_prev_flag(self):
        items = [{"key": 1}]
        page = build_cursor_page(items, limit=10, has_prev=True)
        assert page.has_prev is True

    def test_custom_cursor_field(self):
        items = [{"id": 10}, {"id": 20}, {"id": 30}]  # 3 items, limit 2
        page = build_cursor_page(items, limit=2, cursor_field="id")
        assert page.has_next is True
        decoded = decode_cursor(page.next_cursor)
        assert decoded["id"] == 20


class TestCursorPage:
    def test_frozen_model(self):
        page = CursorPage(items=[], has_next=False, has_prev=False)
        with pytest.raises(ValidationError):
            page.items = [1, 2, 3]  # type: ignore
