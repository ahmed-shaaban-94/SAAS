"""OpenRouter API client for AI-Light."""

from __future__ import annotations

import json

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
        resp = httpx.post(
            OPENROUTER_API_URL,
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
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
            # Remove first and last lines (code fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
