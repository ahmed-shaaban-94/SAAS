"""Slack notification helpers.

Best-effort delivery — if Slack is unreachable, we log and move on.
Replaces the n8n notification sub-workflows (2.6.1, 2.6.2, 2.6.4).
"""

from __future__ import annotations

import httpx

from datapulse.config import get_settings
from datapulse.logging import get_logger

log = get_logger(__name__)


def _send_slack(channel: str, text: str, icon: str = ":robot_face:") -> None:
    """Post a message to Slack via webhook. Best-effort, never raises."""
    url = get_settings().slack_webhook_url
    if not url:
        log.debug("slack_disabled", detail="SLACK_WEBHOOK_URL is empty")
        return
    try:
        httpx.post(
            url,
            json={
                "channel": channel,
                "text": text,
                "username": "DataPulse Bot",
                "icon_emoji": icon,
            },
            timeout=10.0,
        )
        log.info("slack_sent", channel=channel)
    except (httpx.HTTPError, OSError) as exc:
        log.warning("slack_failed", channel=channel, error=str(exc))


def notify_pipeline_success(
    run_id: str,
    duration_seconds: float | None = None,
    rows_loaded: int | None = None,
) -> None:
    """Send pipeline success notification to Slack."""
    text = (
        f":white_check_mark: *Pipeline completed successfully*\n"
        f"Run ID: `{run_id}`\n"
        f"Duration: {duration_seconds or '?'}s\n"
        f"Rows loaded: {rows_loaded or '?'}"
    )
    _send_slack("#datapulse-pipeline", text, ":white_check_mark:")


def notify_pipeline_failure(
    run_id: str,
    stage: str,
    error_message: str,
) -> None:
    """Send pipeline failure alert to Slack."""
    text = (
        f":x: <!channel> *PIPELINE FAILED*\n"
        f"Run ID: `{run_id}`\n"
        f"Stage: {stage}\n"
        f"Error: {error_message}"
    )
    _send_slack("#datapulse-alerts", text, ":x:")


def notify_health_failure(status: str, details: str) -> None:
    """Send health check failure alert."""
    text = f":warning: *DataPulse API health check FAILED*\nStatus: {status}\nDetails: {details}"
    _send_slack("#datapulse-alerts", text, ":warning:")


def notify_quality_digest(
    run_id: str,
    status: str,
    total_checks: int,
    checks_passed: int,
) -> None:
    """Send daily quality digest to Slack."""
    text = (
        f":bar_chart: *Daily Quality Digest*\n"
        f"Last run: `{run_id}`\n"
        f"Status: {status}\n"
        f"Quality checks: {checks_passed}/{total_checks} passed"
    )
    _send_slack("#datapulse-pipeline", text, ":bar_chart:")


def notify_ai_digest(narrative: str, highlights: list[str], anomaly_count: int) -> None:
    """Send daily AI insights digest to Slack."""
    highlights_text = "\n".join(f"  • {h}" for h in highlights) if highlights else "  None"
    text = (
        f":brain: *DataPulse AI Daily Digest*\n\n"
        f"*Executive Summary:*\n{narrative}\n\n"
        f"*Highlights:*\n{highlights_text}\n\n"
        f"*Anomalies Detected:* {anomaly_count}"
    )
    _send_slack("#datapulse-pipeline", text, ":brain:")
