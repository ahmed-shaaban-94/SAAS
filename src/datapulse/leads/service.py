"""Lead capture service — orchestrates dedup check, insert, and CRM webhook."""

from __future__ import annotations

import threading

from datapulse.logging import get_logger

from .models import LeadRequest, LeadResponse
from .repository import LeadRepository

log = get_logger(__name__)


def _fire_webhook(url: str, payload: dict) -> None:
    """POST lead payload to a webhook URL in a background thread (fire-and-forget)."""
    import json as _json
    import urllib.request

    if not url.startswith(("https://", "http://")):
        log.warning("lead_webhook_skipped", reason="URL must use http(s) scheme", url=url)
        return
    try:
        body = _json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5):  # nosec B310 — scheme validated above
            pass
        log.info("lead_webhook_sent", url=url)
    except Exception as exc:
        log.warning("lead_webhook_failed", url=url, error=str(exc))


class LeadService:
    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    def capture(self, data: LeadRequest) -> LeadResponse:
        if self._repo.email_exists(data.email):
            return LeadResponse(success=True, message="You're already on the list!")
        self._repo.insert(
            email=data.email,
            name=data.name,
            company=data.company,
            use_case=data.use_case,
            team_size=data.team_size,
            tier=data.tier,
        )
        self._notify(data)
        return LeadResponse(success=True, message="You're on the list! We'll be in touch soon.")

    def _notify(self, data: LeadRequest) -> None:
        from datapulse.core.config import get_settings

        url = get_settings().lead_notify_url
        if not url:
            return
        payload = {
            "email": data.email,
            "name": data.name,
            "company": data.company,
            "use_case": data.use_case,
            "team_size": data.team_size,
            "tier": data.tier,
        }
        threading.Thread(target=_fire_webhook, args=(url, payload), daemon=True).start()
