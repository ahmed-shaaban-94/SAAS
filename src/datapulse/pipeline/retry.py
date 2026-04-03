"""Retry logic for pipeline stages with exponential backoff.

Provides a decorator that catches transient exceptions and retries
with configurable exponential backoff before giving up.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any

from datapulse.logging import get_logger

log = get_logger(__name__)

TRANSIENT_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class RetryExhaustedError(Exception):
    """All retry attempts have been exhausted for a pipeline stage."""

    def __init__(self, stage: str, attempts: int, last_error: Exception):
        self.stage = stage
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Stage '{stage}' failed after {attempts} attempts: {last_error}")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    retryable: tuple[type[Exception], ...] = TRANSIENT_EXCEPTIONS,
) -> Callable:
    """Retry decorator with exponential backoff for pipeline stages.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        base_delay: Initial delay in seconds before first retry.
        backoff_factor: Multiplier applied to delay on each subsequent retry.
        retryable: Tuple of exception types that trigger a retry.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable as exc:
                    last_error = exc
                    if attempt < max_attempts:
                        delay = base_delay * (backoff_factor ** (attempt - 1))
                        log.warning(
                            "stage_retry",
                            stage=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay_seconds=delay,
                            error=str(exc),
                        )
                        time.sleep(delay)
                    else:
                        log.error(
                            "stage_retry_exhausted",
                            stage=func.__name__,
                            attempts=max_attempts,
                            error=str(exc),
                        )
            raise RetryExhaustedError(func.__name__, max_attempts, last_error)  # type: ignore[arg-type]

        return wrapper

    return decorator
