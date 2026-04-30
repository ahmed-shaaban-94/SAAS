"""Custom Prometheus metrics for DataPulse observability.

Registered in the global prometheus_client registry and automatically
exposed via the ``/metrics`` endpoint set up by
``prometheus_fastapi_instrumentator`` in ``api/app.py``.
"""

from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram

    # -- Database connection pool --
    db_pool_checked_out = Gauge(
        "datapulse_db_pool_checked_out",
        "DB connections currently checked out of the pool",
    )
    db_pool_overflow = Gauge(
        "datapulse_db_pool_overflow",
        "DB connections in overflow above pool_size",
    )
    db_pool_size_total = Gauge(
        "datapulse_db_pool_size_total",
        "Maximum connections (pool_size + max_overflow)",
    )

    # -- Scheduler --
    scheduler_is_leader = Gauge(
        "datapulse_scheduler_is_leader",
        "1 if this worker holds the scheduler advisory lock, 0 otherwise",
    )
    scheduler_jobs_executed = Counter(
        "datapulse_scheduler_jobs_executed_total",
        "Number of scheduled job executions",
        ["job"],
    )

    # -- Pipeline --
    pipeline_runs_total = Counter(
        "datapulse_pipeline_runs_total",
        "Pipeline runs by final status",
        ["status"],
    )
    pipeline_duration_seconds = Histogram(
        "datapulse_pipeline_duration_seconds",
        "Pipeline run duration in seconds",
        buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600),
    )
    pipeline_stale_detected = Counter(
        "datapulse_pipeline_stale_detected_total",
        "Pipeline runs marked failed due to heartbeat timeout",
    )

    # -- Read replica (#608) --
    db_replica_hits = Counter(
        "datapulse_db_replica_hits_total",
        "Sessions served by the read replica engine",
    )
    db_replica_fallbacks = Counter(
        "datapulse_db_replica_fallbacks_total",
        "Readonly sessions that fell back to the primary engine",
        ["reason"],  # "unconfigured", "error"
    )

    # -- POS idempotency / retry observability --
    pos_idempotency_events_total = Counter(
        "datapulse_pos_idempotency_events_total",
        "POS idempotency events by endpoint template, event, and HTTP status",
        ["event", "endpoint", "status"],
    )

    METRICS_AVAILABLE = True

except ImportError:
    # prometheus_client not installed — provide no-op stubs
    METRICS_AVAILABLE = False

    class _NoOp:
        """No-op metric stand-in when prometheus_client is absent."""

        def set(self, *a, **kw): ...
        def inc(self, *a, **kw): ...
        def observe(self, *a, **kw): ...
        def labels(self, *a, **kw):
            return self

    db_pool_checked_out = _NoOp()  # type: ignore[assignment]
    db_pool_overflow = _NoOp()  # type: ignore[assignment]
    db_pool_size_total = _NoOp()  # type: ignore[assignment]
    scheduler_is_leader = _NoOp()  # type: ignore[assignment]
    scheduler_jobs_executed = _NoOp()  # type: ignore[assignment]
    pipeline_runs_total = _NoOp()  # type: ignore[assignment]
    pipeline_duration_seconds = _NoOp()  # type: ignore[assignment]
    pipeline_stale_detected = _NoOp()  # type: ignore[assignment]
    db_replica_hits = _NoOp()  # type: ignore[assignment]
    db_replica_fallbacks = _NoOp()  # type: ignore[assignment]
    pos_idempotency_events_total = _NoOp()  # type: ignore[assignment]
