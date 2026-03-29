"""Audit logging — async DB writer for API request tracking."""

from __future__ import annotations

import contextlib
import json
import threading
from queue import Empty, Queue

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = structlog.get_logger()

# In-memory queue for non-blocking audit writes
_audit_queue: Queue[dict] = Queue(maxsize=10_000)
_writer_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _classify_action(method: str, path: str) -> str:
    """Derive a human-readable action label from method + path."""
    if path == "/health":
        return "health_check"
    if "/pipeline/trigger" in path:
        return "pipeline_trigger"
    if "/pipeline/execute" in path:
        return "pipeline_execute"
    if "/pipeline" in path:
        return "pipeline_query"
    if "/ai-light" in path:
        return "ai_light_query"
    if "/analytics" in path:
        return "analytics_query"
    return f"{method.lower()}_{path}"


def enqueue_audit(
    *,
    method: str,
    path: str,
    ip_address: str | None,
    user_agent: str | None,
    query_params: dict | None,
    response_status: int,
    duration_ms: float,
) -> None:
    """Non-blocking enqueue of an audit record."""
    with contextlib.suppress(Exception):
        _audit_queue.put_nowait({
            "action": _classify_action(method, path),
            "endpoint": path,
            "method": method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_params": query_params or {},
            "response_status": response_status,
            "duration_ms": duration_ms,
        })


def _writer_loop(database_url: str) -> None:
    """Background thread that flushes audit records to PostgreSQL."""
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)

    insert_sql = text(
        "INSERT INTO public.audit_log "
        "(action, endpoint, method, ip_address, user_agent, request_params, "
        "response_status, duration_ms) "
        "VALUES (:action, :endpoint, :method, :ip_address, :user_agent, "
        "CAST(:request_params AS jsonb), :response_status, :duration_ms)"
    )

    while not _stop_event.is_set():
        batch: list[dict] = []
        try:
            # Block up to 2 seconds for the first item
            item = _audit_queue.get(timeout=2.0)
            batch.append(item)
            # Drain remaining items (up to 100 per flush)
            while len(batch) < 100:
                try:
                    batch.append(_audit_queue.get_nowait())
                except Empty:
                    break
        except Empty:
            continue

        if not batch:
            continue

        try:
            session = session_factory()
            try:
                for record in batch:
                    record["request_params"] = json.dumps(record["request_params"])
                    session.execute(insert_sql, record)
                session.commit()
            except Exception as exc:
                session.rollback()
                logger.warning("audit_write_failed", error=str(exc), batch_size=len(batch))
            finally:
                session.close()
        except Exception as exc:
            logger.warning("audit_session_failed", error=str(exc))


def start_audit_writer(database_url: str) -> None:
    """Start the background audit writer thread."""
    global _writer_thread
    if _writer_thread is not None and _writer_thread.is_alive():
        return
    _stop_event.clear()
    _writer_thread = threading.Thread(
        target=_writer_loop, args=(database_url,), daemon=True, name="audit-writer"
    )
    _writer_thread.start()
    logger.info("audit_writer_started")


def stop_audit_writer() -> None:
    """Signal the audit writer thread to stop."""
    _stop_event.set()
    if _writer_thread is not None:
        _writer_thread.join(timeout=5.0)
