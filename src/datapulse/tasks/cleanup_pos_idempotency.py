"""Nightly cleanup of expired POS idempotency keys.

Run from an ops cron / scheduler entry (n8n workflow, systemd timer, …).
Safe to run multiple times per day; idempotent — keys with
``expires_at < now()`` are deleted.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §6.5.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def run(session: Session) -> int:
    """Delete every row whose ``expires_at`` is in the past. Returns the count."""
    result = session.execute(text("DELETE FROM pos.idempotency_keys WHERE expires_at < now()"))
    # ``rowcount`` is SQLAlchemy Core and typed as ``int | None``; the mypy
    # stubs for Result[Any] omit it. We access it dynamically with getattr.
    rowcount = getattr(result, "rowcount", 0) or 0
    return int(rowcount)


if __name__ == "__main__":  # pragma: no cover
    from datapulse.core.db import get_session_factory
    from datapulse.logging import get_logger

    log = get_logger(__name__)
    factory = get_session_factory()
    with factory() as session:
        deleted = run(session)
        session.commit()
        log.info("pos_idempotency_cleanup_complete", deleted=deleted)
