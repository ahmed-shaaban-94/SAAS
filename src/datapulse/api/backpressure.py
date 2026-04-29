"""Application-level admission control for graceful overload handling."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from fastapi import Request

_EXEMPT_PATHS = (
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
    "/openapi.json",
    "/docs",
    "/redoc",
)


class AdmissionController:
    """Bound in-flight request concurrency to fail fast under load."""

    def __init__(self, max_in_flight_requests: int, acquire_timeout_ms: int) -> None:
        self.max_in_flight_requests = max(0, max_in_flight_requests)
        self.acquire_timeout_ms = max(0, acquire_timeout_ms)
        self._semaphore = (
            asyncio.Semaphore(self.max_in_flight_requests)
            if self.max_in_flight_requests > 0
            else None
        )

    @property
    def enabled(self) -> bool:
        return self._semaphore is not None

    @property
    def in_flight(self) -> int:
        if self._semaphore is None:
            return 0
        return max(0, self.max_in_flight_requests - self._semaphore._value)

    def is_exempt(self, request: Request) -> bool:
        if request.method == "OPTIONS":
            return True
        path = request.url.path
        return path in _EXEMPT_PATHS

    async def try_acquire(self) -> bool:
        if self._semaphore is None:
            return True

        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.acquire_timeout_ms / 1000,
            )
            return True
        except TimeoutError:
            return False

    def release(self) -> None:
        if self._semaphore is None:
            return
        with suppress(ValueError):
            self._semaphore.release()


from datapulse.tasks.queue import queue_depth as _queue_depth_probe  # noqa: E402

# Module-level alias so tests can monkeypatch a single symbol.
queue_depth = _queue_depth_probe


class QueueDepthGuard:
    """Reject requests when the Arq queue is saturated (cluster-wide signal)."""

    def __init__(self, limit: int) -> None:
        self.limit = max(0, limit)

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    async def allow(self) -> bool:
        if not self.enabled:
            return True
        try:
            depth = await queue_depth()
        except Exception:  # noqa: BLE001
            return True  # fail open
        return depth < self.limit
