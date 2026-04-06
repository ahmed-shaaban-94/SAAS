"""Tests for datapulse.notifications — Slack webhook helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from datapulse.notifications import (
    _send_slack,
    notify_ai_digest,
    notify_health_failure,
    notify_pipeline_failure,
    notify_pipeline_success,
    notify_quality_digest,
)


# ---------------------------------------------------------------------------
# _send_slack
# ---------------------------------------------------------------------------


def test_send_slack_skips_when_no_webhook():
    """No HTTP call when SLACK_WEBHOOK_URL is empty."""
    with (
        patch("datapulse.notifications.get_settings") as mock_settings,
        patch("datapulse.notifications.httpx") as mock_httpx,
    ):
        mock_settings.return_value = MagicMock(slack_webhook_url="")
        _send_slack("#test", "hello")
        mock_httpx.post.assert_not_called()


def test_send_slack_posts_to_webhook():
    """Sends JSON payload to Slack webhook URL."""
    with (
        patch("datapulse.notifications.get_settings") as mock_settings,
        patch("datapulse.notifications.httpx") as mock_httpx,
    ):
        mock_settings.return_value = MagicMock(slack_webhook_url="https://hooks.slack.com/test")
        _send_slack("#alerts", "test message", ":bell:")

        mock_httpx.post.assert_called_once()
        call_kwargs = mock_httpx.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["channel"] == "#alerts"
        assert payload["text"] == "test message"
        assert payload["icon_emoji"] == ":bell:"


def test_send_slack_swallows_exceptions():
    """Slack failures are logged but never raised."""
    with (
        patch("datapulse.notifications.get_settings") as mock_settings,
        patch("datapulse.notifications.httpx") as mock_httpx,
    ):
        mock_settings.return_value = MagicMock(slack_webhook_url="https://hooks.slack.com/test")
        mock_httpx.post.side_effect = ConnectionError("network error")

        # Should not raise
        _send_slack("#test", "hello")


# ---------------------------------------------------------------------------
# High-level notification functions
# ---------------------------------------------------------------------------


def test_notify_pipeline_success():
    """Pipeline success notification includes run_id and rows."""
    with patch("datapulse.notifications._send_slack") as mock_send:
        notify_pipeline_success("run-123", duration_seconds=45.2, rows_loaded=5000)
        mock_send.assert_called_once()
        text_arg = mock_send.call_args[0][1]
        assert "run-123" in text_arg
        assert "5000" in text_arg


def test_notify_pipeline_failure():
    """Pipeline failure notification includes stage and error."""
    with patch("datapulse.notifications._send_slack") as mock_send:
        notify_pipeline_failure("run-456", "silver", "column not found")
        mock_send.assert_called_once()
        text_arg = mock_send.call_args[0][1]
        assert "silver" in text_arg
        assert "column not found" in text_arg


def test_notify_health_failure():
    """Health failure notification includes status."""
    with patch("datapulse.notifications._send_slack") as mock_send:
        notify_health_failure("error", "connection refused")
        mock_send.assert_called_once()
        text_arg = mock_send.call_args[0][1]
        assert "error" in text_arg


def test_notify_quality_digest():
    """Quality digest includes check counts."""
    with patch("datapulse.notifications._send_slack") as mock_send:
        notify_quality_digest("run-789", "success", total_checks=10, checks_passed=9)
        mock_send.assert_called_once()
        text_arg = mock_send.call_args[0][1]
        assert "9/10" in text_arg


def test_notify_ai_digest():
    """AI digest includes narrative and anomaly count."""
    with patch("datapulse.notifications._send_slack") as mock_send:
        notify_ai_digest(
            narrative="Revenue up 5%",
            highlights=["Product A grew 20%"],
            anomaly_count=3,
        )
        mock_send.assert_called_once()
        text_arg = mock_send.call_args[0][1]
        assert "Revenue up 5%" in text_arg
        assert "3" in text_arg


def test_notify_ai_digest_no_highlights():
    """AI digest handles empty highlights list."""
    with patch("datapulse.notifications._send_slack") as mock_send:
        notify_ai_digest(narrative="All quiet", highlights=[], anomaly_count=0)
        mock_send.assert_called_once()
        text_arg = mock_send.call_args[0][1]
        assert "None" in text_arg
