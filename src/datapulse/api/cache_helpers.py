"""Shared HTTP cache-control helpers for API route handlers."""

from __future__ import annotations

from fastapi import Response


def set_cache_headers(response: Response, max_age: int) -> None:
    """Set Cache-Control header for browser caching (always private for RLS)."""
    response.headers["Cache-Control"] = f"max-age={max_age}, private"
