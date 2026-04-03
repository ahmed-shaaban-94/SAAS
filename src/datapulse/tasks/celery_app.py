"""Celery application configuration.

Uses the existing Redis instance as both broker and result backend.
The API service uses db 0 for caching; Celery uses db 1 for broker
and db 2 for results to avoid key collisions.
"""

from __future__ import annotations

from celery import Celery

from datapulse.config import get_settings


def _redis_url(db: int) -> str:
    """Derive a Redis URL for a specific database index.

    Replaces the trailing ``/0`` (or appends ``/N``) so that broker and
    result backend use separate Redis databases.
    """
    base = get_settings().redis_url
    if not base:
        return f"redis://localhost:6379/{db}"
    # Strip trailing /N if present, then append our db
    parts = base.rsplit("/", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]}/{db}"
    return f"{base.rstrip('/')}/{db}"


celery_app = Celery("datapulse")

celery_app.conf.update(
    broker_url=_redis_url(1),
    result_backend=_redis_url(2),
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Result expiry — 1 hour
    result_expires=3600,
    # Task settings
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Concurrency — conservative for DB-bound tasks
    worker_concurrency=4,
    # Task timeouts — prevent hung workers
    task_time_limit=600,  # 10 min hard kill (SIGKILL)
    task_soft_time_limit=540,  # 9 min soft warning (SoftTimeLimitExceeded)
)

# Auto-discover task modules
celery_app.autodiscover_tasks(["datapulse.tasks"])
