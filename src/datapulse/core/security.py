"""Timing-safe comparison helpers for authentication secrets.

Uses ``hmac.compare_digest`` to prevent timing side-channel attacks
when comparing API keys, tokens, and other secret values.
"""

from __future__ import annotations

import hmac


def compare_secrets(provided: str, expected: str) -> bool:
    """Compare two secret strings in constant time.

    Returns True if the strings match, False otherwise.
    Both values are encoded to bytes before comparison to ensure
    ``hmac.compare_digest`` operates correctly.
    """
    return hmac.compare_digest(
        provided.encode("utf-8"),
        expected.encode("utf-8"),
    )
