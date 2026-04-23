"""SSE streaming helper for notification unread counts.

Hoisted out of :mod:`datapulse.api.routes.notifications` so the route file
does not need to import :class:`NotificationRepository` directly (issue #542).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable

from datapulse.core.db import tenant_session_scope
from datapulse.notifications_center.repository import NotificationRepository


async def iter_unread_count_events(
    user_id: str,
    tenant_id: str,
    is_disconnected: Callable[[], Awaitable[bool]],
    poll_interval: float = 5.0,
) -> AsyncGenerator[str, None]:
    """Yield SSE ``count``/``error`` events whenever the unread count changes.

    Each poll opens a short-lived session, scopes it to the caller's tenant
    via ``SET LOCAL app.tenant_id``, reads the current unread count through
    :class:`NotificationRepository`, and emits an event only when the value
    moved. The loop exits when ``is_disconnected()`` returns True.
    """
    last_count = -1
    while True:
        if await is_disconnected():
            break
        try:
            with tenant_session_scope(
                tenant_id,
                statement_timeout="10s",
                session_type="notifications_stream",
            ) as session:
                repo = NotificationRepository(session)
                count = repo.unread_count(user_id)
                if count != last_count:
                    last_count = count
                    data = json.dumps({"unread": count})
                    yield f"event: count\ndata: {data}\n\n"
        except Exception:
            yield "event: error\ndata: {}\n\n"
        await asyncio.sleep(poll_interval)
