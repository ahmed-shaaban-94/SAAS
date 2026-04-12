"""Gunicorn configuration for DataPulse API.

Gunicorn replaces raw uvicorn multi-worker mode, providing:
- Automatic restart of crashed workers (uvicorn does not do this)
- Worker timeout (kills stuck workers after 120s)
- Max-requests recycling (prevents memory leaks from long-lived workers)
- post_fork hook to enable scheduler in only one worker via file lock
"""

import os

# Worker class -- Gunicorn manages processes, Uvicorn handles async I/O
worker_class = "uvicorn.workers.UvicornWorker"

# Number of workers -- overridable via WEB_CONCURRENCY env var
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))

# Bind address
bind = os.environ.get("BIND", "0.0.0.0:8000")

# Timeouts
timeout = 120          # Kill worker if no heartbeat in 120s
graceful_timeout = 30  # 30s to finish in-flight requests on SIGTERM
keepalive = 75         # Match nginx keepalive_timeout 65s (must be higher)

# Max requests per worker -- prevents slow memory leaks.
# Jitter randomizes restart so not all workers recycle simultaneously.
max_requests = 1000
max_requests_jitter = 100

# Logging -- let structlog handle formatting, Gunicorn just forwards
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Preload app -- disabled because FastAPI factory pattern requires
# per-worker app creation (each worker calls create_app()).
preload_app = False


def post_fork(server, worker):
    """Enable scheduler in exactly one worker using a file lock.

    The first worker to acquire the lock gets SCHEDULER_ENABLED=true.
    If that worker dies, the OS releases the lock, and the replacement
    worker (spawned by Gunicorn) acquires it in its own post_fork call.
    """
    import fcntl

    lock_path = "/tmp/datapulse-scheduler.lock"
    try:
        fd = open(lock_path, "w")  # noqa: SIM115 — intentionally kept open as lock
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Keep fd open -- lock lives as long as the worker process
        worker._scheduler_lock_fd = fd
        os.environ["SCHEDULER_ENABLED"] = "true"
        server.log.info(f"Worker {worker.pid}: scheduler ENABLED")
    except (BlockingIOError, OSError):
        os.environ["SCHEDULER_ENABLED"] = "false"
        server.log.info(f"Worker {worker.pid}: scheduler disabled")
