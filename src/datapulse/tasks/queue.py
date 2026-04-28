"""Async singleton wrapping arq.create_pool — enqueue + depth probes."""

from __future__ import annotations

import asyncio

from arq import create_pool
from arq.connections import ArqRedis

from datapulse.config import get_settings
from datapulse.logging import get_logger
from datapulse.tasks.worker import _redis_settings

log = get_logger(__name__)

_pool: ArqRedis | None = None
_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis | None:
    """Return a process-wide ArqRedis pool, creating it on first use.

    Returns None if Redis is misconfigured — callers degrade gracefully.
    """
    global _pool
    if _pool is not None:
        return _pool
    async with _lock:
        if _pool is not None:
            return _pool
        try:
            _pool = await create_pool(_redis_settings())
        except Exception as exc:  # noqa: BLE001
            log.error("arq_pool_create_failed", error=str(exc))
            return None
        return _pool


async def close_arq_pool() -> None:
    """Close the pool and reset the singleton (used on shutdown)."""
    global _pool
    if _pool is None:
        return
    try:
        await _pool.close(close_connection_pool=True)
    finally:
        _pool = None


async def queue_depth() -> int:
    """Best-effort sample of pending jobs. Returns 0 on probe failure."""
    pool = await get_arq_pool()
    if pool is None:
        return 0
    try:
        queue_name = get_settings().arq_queue_name
        return int(await pool.zcard(queue_name))
    except Exception as exc:  # noqa: BLE001
        log.warning("arq_queue_depth_probe_failed", error=str(exc))
        return 0
