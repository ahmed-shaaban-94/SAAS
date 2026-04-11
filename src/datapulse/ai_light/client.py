"""OpenRouter API client for AI-Light."""

from __future__ import annotations

import json
import time

import httpx

from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    """Thin wrapper around the OpenRouter chat completions API."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Send a chat completion request and return the assistant message."""
        if not self.is_configured:
            raise RuntimeError("OpenRouter API key not configured (OPENROUTER_API_KEY)")

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

        # Retry with exponential backoff for transient failures
        # NOTE: time.sleep() blocks the current threadpool worker. In a
        # high-concurrency deployment this should be replaced with an async
        # client (httpx.AsyncClient) and asyncio.sleep(). Acceptable for now
        # given low expected request volume to the AI-Light endpoints.
        max_retries = 3
        resp = None
        for attempt in range(max_retries):
            try:
                resp = httpx.post(
                    OPENROUTER_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=60,
                )
                resp.raise_for_status()
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                wait = 2**attempt
                log.warning(
                    "openrouter_retry",
                    attempt=attempt + 1,
                    wait_seconds=wait,
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
