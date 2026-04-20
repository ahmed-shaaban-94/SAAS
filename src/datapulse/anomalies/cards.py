"""Adapter — convert persisted ``AnomalyAlertResponse`` rows to ``AnomalyCard`` display rows.

The persisted shape captures statistical facts (z-score, expected value,
severity tier). The card shape captures *what to show a human* (title,
body, kind, confidence). Keeping this as a pure function makes the mapping
trivially testable and keeps the service layer thin.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from datapulse.anomalies.models import AnomalyAlertResponse, AnomalyCard

# Detector-level direction -> design-level card kind.
# Suppressed alerts fall back to "info" regardless of direction.
_DIRECTION_TO_KIND: dict[str, str] = {
    "spike": "up",
    "drop": "down",
    "up": "up",
    "down": "down",
}

# Detector-level severity -> design-level confidence.
# "critical" and "high" both map to "high" so the card can render a hot badge.
_SEVERITY_TO_CONFIDENCE: dict[str, str] = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

# Human-friendly metric labels for title lines.
_METRIC_LABELS: dict[str, str] = {
    "daily_gross_sales": "Daily revenue",
    "daily_transactions": "Daily orders",
    "daily_returns": "Daily returns",
    "daily_customers": "Daily customers",
}


def _pct_change(actual: Decimal, expected: Decimal) -> Decimal | None:
    """Compute percent delta; return None when expected is zero."""
    if expected == 0:
        return None
    return (actual - expected) / expected * Decimal(100)


def _time_ago(period: date, today: date | None = None) -> str:
    """Render a relative-day label — persisted alerts are day-grained."""
    today = today or date.today()
    days = (today - period).days
    if days <= 0:
        return "today"
    if days == 1:
        return "1d ago"
    return f"{days}d ago"


def _format_pct(pct: Decimal) -> str:
    """Render a percent with one decimal and sign-aware symbol."""
    magnitude = abs(pct).quantize(Decimal("0.1"))
    return f"{magnitude}%"


def to_card(alert: AnomalyAlertResponse, today: date | None = None) -> AnomalyCard:
    """Project a persisted alert to its display card."""
    metric_label = _METRIC_LABELS.get(alert.metric, alert.metric.replace("_", " "))

    if alert.is_suppressed:
        kind = "info"
        confidence = "info"
    else:
        kind = _DIRECTION_TO_KIND.get(alert.direction, "info")
        confidence = _SEVERITY_TO_CONFIDENCE.get(alert.severity, "low")

    pct = _pct_change(alert.actual_value, alert.expected_value)
    arrow = "up" if kind == "up" else "down" if kind == "down" else ""

    if pct is not None and arrow:
        title = f"{metric_label} {arrow} {_format_pct(pct)}"
    else:
        title = metric_label

    body_parts = [
        f"Observed {alert.actual_value}",
        f"expected ~{alert.expected_value}",
    ]
    if alert.z_score is not None:
        body_parts.append(f"z={alert.z_score}")
    if alert.is_suppressed and alert.suppression_reason:
        body_parts.append(f"suppressed ({alert.suppression_reason})")
    body = ". ".join(body_parts) + "."

    return AnomalyCard(
        id=alert.id,
        kind=kind,
        title=title,
        body=body,
        time_ago=_time_ago(alert.period, today),
        confidence=confidence,
    )
