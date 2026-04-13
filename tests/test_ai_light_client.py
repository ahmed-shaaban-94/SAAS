"""Tests for datapulse.ai_light.client — OpenRouter API client.

Covers:
- Configured / unconfigured state
- Successful chat + JSON parsing
- Retry behaviour (transport errors)
- Exponential backoff: wait grows as min(2^attempt + jitter, 8)
- Circuit breaker: opens after threshold, resets on success, half-open probe
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from datapulse.ai_light.client import (
    _CB_OPEN_SECONDS,
    _CB_THRESHOLD,
    OpenRouterClient,
)


@pytest.fixture()
def configured_client():
    settings = MagicMock()
    settings.openrouter_api_key = "test-key-123"
    settings.openrouter_model = "meta-llama/llama-3.1-8b-instruct:free"
    return OpenRouterClient(settings)


@pytest.fixture()
def unconfigured_client():
    settings = MagicMock()
    settings.openrouter_api_key = ""
    settings.openrouter_model = "test-model"
    return OpenRouterClient(settings)


class TestIsConfigured:
    def test_configured(self, configured_client):
        assert configured_client.is_configured is True

    def test_not_configured(self, unconfigured_client):
        assert unconfigured_client.is_configured is False


class TestChat:
    def test_chat_not_configured_raises(self, unconfigured_client):
        with pytest.raises(RuntimeError, match="not configured"):
            unconfigured_client.chat("sys", "user")

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_success(self, mock_post, configured_client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "AI response here"}}],
            "usage": {"total_tokens": 100},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = configured_client.chat("system prompt", "user message")
        assert result == "AI response here"
        mock_post.assert_called_once()

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_bad_response_structure(self, mock_post, configured_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": []}  # empty choices
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Unexpected response"):
            configured_client.chat("sys", "user")

    @patch("datapulse.ai_light.client.time.sleep")
    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_retry_on_transport_error(self, mock_post, mock_sleep, configured_client):
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        # Fail twice, succeed third
        mock_post.side_effect = [
            httpx.TransportError("conn reset"),
            httpx.TransportError("conn reset"),
            mock_resp,
        ]

        result = configured_client.chat("sys", "user")
        assert result == "ok"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("datapulse.ai_light.client.time.sleep")
    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_all_retries_fail(self, mock_post, mock_sleep, configured_client):
        import httpx

        mock_post.side_effect = httpx.TransportError("down")

        with pytest.raises(httpx.TransportError):
            configured_client.chat("sys", "user")
        assert mock_post.call_count == 3


class TestChatJson:
    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_json_success(self, mock_post, configured_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = configured_client.chat_json("sys", "user")
        assert result == {"key": "value"}

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_json_strips_markdown_fences(self, mock_post, configured_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '```json\n{"a": 1}\n```'}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = configured_client.chat_json("sys", "user")
        assert result == {"a": 1}

    @patch("datapulse.ai_light.client.httpx.post")
    def test_chat_json_parse_error(self, mock_post, configured_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "not valid json"}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Failed to parse"):
            configured_client.chat_json("sys", "user")


class TestExponentialBackoff:
    """Verify backoff grows as min(2^attempt + jitter, 8) and is capped."""

    @patch("datapulse.ai_light.client.random.uniform", return_value=0.0)
    @patch("datapulse.ai_light.client.time.sleep")
    @patch("datapulse.ai_light.client.httpx.post")
    def test_backoff_grows_exponentially(self, mock_post, mock_sleep, mock_rand, configured_client):
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        # Fail twice, succeed on third attempt.
        mock_post.side_effect = [
            httpx.TransportError("err"),
            httpx.TransportError("err"),
            mock_resp,
        ]

        configured_client.chat("sys", "user")

        # With jitter=0: attempt 0 → 2^0 = 1s, attempt 1 → 2^1 = 2s.
        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert sleep_calls == pytest.approx([1.0, 2.0], abs=0.01)

    @patch("datapulse.ai_light.client.random.uniform", return_value=0.0)
    @patch("datapulse.ai_light.client.time.sleep")
    @patch("datapulse.ai_light.client.httpx.post")
    def test_backoff_does_not_exceed_cap(self, mock_post, mock_sleep, mock_rand, configured_client):
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.side_effect = [
            httpx.TransportError("err"),
            httpx.TransportError("err"),
            mock_resp,
        ]

        configured_client.chat("sys", "user")

        for sleep_val in [c.args[0] for c in mock_sleep.call_args_list]:
            assert sleep_val <= 8.0


class TestCircuitBreaker:
    """Verify the circuit breaker opens, stays open, and resets correctly."""

    def test_open_circuit_rejects_immediately(self, configured_client):
        """When the circuit is open, chat() raises without calling httpx."""
        configured_client._cb_failures = _CB_THRESHOLD
        configured_client._cb_open_until = time.time() + _CB_OPEN_SECONDS

        with pytest.raises(RuntimeError, match="circuit breaker open"):
            configured_client.chat("sys", "user")

    @patch("datapulse.ai_light.client.httpx.post")
    def test_half_open_allows_probe_request(self, mock_post, configured_client):
        """After open_until passes, the circuit is half-open and one request goes through."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "probe ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        # Circuit was open but the timeout has already expired.
        configured_client._cb_failures = _CB_THRESHOLD
        configured_client._cb_open_until = time.time() - 1  # expired

        result = configured_client.chat("sys", "user")

        assert result == "probe ok"
        assert configured_client._cb_failures == 0, "Successful probe must reset failure counter"
        assert configured_client._cb_open_until == 0.0

    @patch("datapulse.ai_light.client.httpx.post")
    def test_success_resets_failure_counter(self, mock_post, configured_client):
        """A successful call resets the circuit-breaker state regardless of prior failures."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        configured_client._cb_failures = _CB_THRESHOLD - 1  # one below threshold

        configured_client.chat("sys", "user")

        assert configured_client._cb_failures == 0

    @patch("datapulse.ai_light.client.time.sleep")
    @patch("datapulse.ai_light.client.httpx.post")
    def test_circuit_opens_after_threshold_failures(self, mock_post, mock_sleep, configured_client):
        """After *_CB_THRESHOLD* consecutive failures, the circuit opens."""
        import httpx

        mock_post.side_effect = httpx.TransportError("down")

        with pytest.raises(httpx.TransportError):
            configured_client.chat("sys", "user")

        assert configured_client._cb_failures >= _CB_THRESHOLD
        assert configured_client._cb_open_until > time.time()
