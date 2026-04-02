"""Tests for datapulse.ai_light.client — OpenRouter API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datapulse.ai_light.client import OpenRouterClient


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
