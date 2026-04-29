"""Lifespan helper — starts the scheduler on the main asyncio thread.

Wrapping ``start_scheduler()`` in ``asyncio.to_thread`` causes
``get_event_loop()`` to fail in Python 3.12 worker threads and hangs
uvicorn at ``Waiting for application startup``. DB ``connect_timeout=10s``
already prevents indefinite hangs.
"""

import contextlib
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

logger = structlog.get_logger()


def build_lifespan():
    """Build the async lifespan context manager for the FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from datapulse.scheduler import start_scheduler, stop_scheduler

        try:
            start_scheduler()
        except Exception:
            logger.error("scheduler_start_failed", exc_info=True)
        yield
        stop_scheduler()
        from datapulse.tasks.queue import close_arq_pool

        with contextlib.suppress(Exception):
            await close_arq_pool()

    return lifespan
