"""Pure mappers from ``AnomalyAlertResponse`` to design-facing ``AnomalyCard``.

Kept dependency-free (no DB, no service) so the mapping rules are easy
to unit-test exhaustively. See #508.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from datapulse.anomalies.models import AnomalyAlertResponse, AnomalyCard

# Direction strings used by the detector — mapped 1:1 onto design "kind".
_DIRECTION_TO_KIND: dict[str, str] = {
    "spike": "up",
    "drop": "down",
    "up": "up",
    "down": "down",
}

# Severity → confidence (design uses high/medium/low/info, not critical).
_SEVERITY_TO_CONFIDENCE: dict[str, str] = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

# Human-readable metric labels for card titles. Falls back to the raw
# metric string prettified if not in the map.
_METRIC_LABELS: dict[str, str] = {
    "daily_gross_sales": "Revenue",
    "daily_gross_amount": "Revenue",
    "daily_transactions": "Orders",
    "daily_returns": "Returns",
    "daily_customers": "Customers",
    "daily_unique_customers": "Customers",
}


def _metric_label(metric: str) -> str:
    if metric in _METRIC_LABELS:
        return _METRIC_LABELS[metric]
    return metric.replace("_", " ").strip().title() or metric


def _fmt_value(value: Decimal) -> str:
    """Display a Decimal without trailing zeros (e.g. ``1200`` not ``1200.0000``)."""
    try:
        normalised = value.normalize()
    except Exception:  # pragma: no cover — Decimal normalise rarely raises
        return str(value)
    sign, digits, exponent = normalised.as_tuple()
    # Avoid scientific notation that ``normalize`` may produce for ints.
    if isinstance(exponent, int) and exponent > 0:
        normalised = normalised.quantize(Decimal(1))
    return format(normalised, "f")


def _time_ago(period: date, today: date) -> str:
    delta = (today - period).days
    if delta <= 0:
        return "today"
    if delta == 1:
        return "1d ago"
    if delta < 7:
        return f"{delta}d ago"
    if delta < 30:
        weeks = delta // 7
        return f"{weeks}w ago" if weeks > 1 else "1w ago"
    months = delta // 30
    return f"{months}mo ago" if months > 1 else "1mo ago"


def _confidence(alert: AnomalyAlertResponse) -> str:
    if alert.is_suppressed:
        return "info"
    return _SEVERITY_TO_CONFIDENCE.get(alert.severity.lower(), "info")


def _kind(alert: AnomalyAlertResponse) -> str:
    if alert.is_suppressed:
        return "info"
    return _DIRECTION_TO_KIND.get(alert.direction.lower(), "info")


def _title(alert: AnomalyAlertResponse) -> str:
    label = _metric_label(alert.metric)
    if alert.is_suppressed:
        return f"{label} flagged (suppressed)"

    expected = Decimal(str(alert.expected_value))
    actual = Decimal(str(alert.actual_value))
    if expected > 0:
        delta_pct = ((actual - expected) / expected * Decimal("100")).quantize(Decimal("1"))
        verb = "up" if alert.direction.lower() in {"spike", "up"} else "down"
        sign = "+" if delta_pct >= 0 else ""
        return f"{label} {verb} {sign}{delta_pct}%"
    verb = "spiked" if alert.direction.lower() in {"spike", "up"} else "dropped"
    return f"{label} {verb} to {_fmt_value(actual)}"


def _body(alert: AnomalyAlertResponse) -> str:
    label = _metric_label(alert.metric)
    actual = _fmt_value(Decimal(str(alert.actual_value)))
    expected = _fmt_value(Decimal(str(alert.expected_value)))

    if alert.is_suppressed:
        reason = alert.suppression_reason or "calendar event"
        return (
            f"Suppressed on {alert.period.isoformat()} — {reason}. "
            f"Actual {label.lower()} {actual} vs expected {expected}."
        )

    parts = [f"{label} on {alert.period.isoformat()} was {actual} (expected {expected})."]
    if alert.z_score is not None:
        z = Decimal(str(alert.z_score)).quantize(Decimal("0.1"))
        parts.append(f"z={z}")
    return " ".join(parts)


def to_anomaly_card(alert: AnomalyAlertResponse, today: date | None = None) -> AnomalyCard:
    """Project an anomaly alert onto the design-facing card shape."""
    ref_today = today or date.today()
    return AnomalyCard(
        id=alert.id,
        kind=_kind(alert),
        title=_title(alert),
        body=_body(alert),
        time_ago=_time_ago(alert.period, ref_today),
        confidence=_confidence(alert),
    )
