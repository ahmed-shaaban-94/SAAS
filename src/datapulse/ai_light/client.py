"""OpenRouter API client for AI-Light."""

from __future__ import annotations

import json
import random
import time

import httpx

from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Circuit-breaker thresholds
_CB_THRESHOLD = 3  # consecutive failures before opening
_CB_OPEN_SECONDS = 60  # seconds the circuit stays open before half-open


class OpenRouterClient:
    """Thin wrapper around the OpenRouter chat completions API.

    Retry strategy: exponential backoff with jitter — wait = min(2^attempt + U(0, 0.5), 8).
    Circuit breaker: after *_CB_THRESHOLD* consecutive failures the circuit opens
    for *_CB_OPEN_SECONDS* seconds.  After that window the circuit moves to half-open
    (one probe request allowed through).  A successful probe resets the counter; a
    failed probe extends the open window by another *_CB_OPEN_SECONDS*.
    """

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model
        # Circuit-breaker state — per-instance so test fixtures remain isolated.
        self._cb_failures: int = 0
        self._cb_open_until: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # Circuit-breaker helpers
    # ------------------------------------------------------------------

    def _cb_is_open(self) -> bool:
        """Return True if the circuit is fully open (requests should be rejected)."""
        return self._cb_failures >= _CB_THRESHOLD and time.time() < self._cb_open_until

    def _cb_record_success(self) -> None:
        """Reset failure counter after a successful request."""
        self._cb_failures = 0
        self._cb_open_until = 0.0

    def _cb_record_failure(self) -> None:
        """Increment failure counter and open the circuit when threshold is reached."""
        self._cb_failures += 1
        if self._cb_failures >= _CB_THRESHOLD:
            self._cb_open_until = time.time() + _CB_OPEN_SECONDS

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Send a chat completion request and return the assistant message."""
        if not self.is_configured:
            raise RuntimeError("OpenRouter API key not configured (OPENROUTER_API_KEY)")

        if self._cb_is_open():
            remaining = self._cb_open_until - time.time()
            raise RuntimeError(f"OpenRouter circuit breaker open — retry after {remaining:.0f}s")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://datapulse.dev",
            "X-Title": "DataPulse AI-Light",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": 1024,
        }

        log.info("openrouter_request", model=self._model)

        # Exponential backoff with jitter: wait = min(2^attempt + U(0, 0.5), 8).
        max_retries = 3
        resp = None
        for attempt in range(max_retries):
            try:
                resp = httpx.post(
                    OPENROUTER_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                self._cb_record_success()
                break
            except Exception as exc:
                self._cb_record_failure()
                if attempt == max_retries - 1:
                    raise
                wait = min(2**attempt + random.uniform(0, 0.5), 8)
                log.warning(
                    "openrouter_retry",
                    attempt=attempt + 1,
                    wait_seconds=round(wait, 2),
                    error=str(exc),
                )
                time.sleep(wait)

        if resp is None:
            raise RuntimeError("OpenRouter request failed: no response after retries")

        data = resp.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:
            log.error("openrouter_bad_response", error=str(exc), data=str(data)[:500])
            raise RuntimeError("Unexpected response structure from OpenRouter") from exc

        log.info(
            "openrouter_response",
            model=self._model,
            tokens=data.get("usage", {}).get("total_tokens"),
        )
        return content

    def chat_json(self, system: str, user: str, temperature: float = 0.1) -> list | dict:
        """Send a chat request expecting JSON back, parse and return."""
        raw = self.chat(system, user, temperature=temperature)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            log.error("openrouter_json_parse_failed", raw=raw[:500], error=str(exc))
            raise RuntimeError(f"Failed to parse AI response as JSON: {exc}") from exc
