"""HMAC-signed HTTP dispatch with exponential backoff retry schedule."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json

import httpx

from datapulse.logging import get_logger

log = get_logger(__name__)

# Retry delays in seconds: 1 min, 5 min, 30 min, 2 h, 8 h
_RETRY_DELAYS = [60, 300, 1800, 7200, 28800]
MAX_ATTEMPTS = len(_RETRY_DELAYS) + 1  # 6 attempts total before dead-lettering


def compute_signature(secret: str, body: bytes) -> str:
    """Return HMAC-SHA256 hex digest for the request body."""
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def next_retry_at(attempt_count: int) -> datetime.datetime | None:
    """Return the UTC timestamp for the next retry, or None if max reached."""
    idx = attempt_count  # attempt_count is 0-based after first try
    if idx >= len(_RETRY_DELAYS):
        return None
    delay = _RETRY_DELAYS[idx]
    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=delay)


def dispatch(target_url: str, secret: str, event_type: str, payload: dict) -> None:
    """Send a single signed webhook POST. Raises on non-2xx or network error."""
    body = json.dumps({"event": event_type, "data": payload}).encode()
    signature = compute_signature(secret, body)
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            target_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-DataPulse-Event": event_type,
                "X-DataPulse-Signature": signature,
            },
        )
        response.raise_for_status()
    log.info(
        "webhook_dispatched", url=target_url, webhook_event=event_type, status=response.status_code
    )
