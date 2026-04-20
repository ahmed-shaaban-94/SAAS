"""Pure mappers for the dashboard top-insight banner (#510).

Picks the single most attention-worthy signal currently in the system —
a high-severity active anomaly — and projects it onto the banner's
display shape with a deep-link CTA.

Kept pure (no DB, no clock, no LLM) so the selection + mapping rules are
easy to unit-test exhaustively.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from datapulse.ai_light.models import TopInsight
from datapulse.anomalies.models import AnomalyAlertResponse

# Severity → confidence (ranking of anomalies uses raw severity).
_SEVERITY_TO_CONFIDENCE: dict[str, str] = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

# Numeric weight for tie-breaking when picking the top anomaly.
_SEVERITY_RANK: dict[str, int] = {"critical": 4, "high": 3, "medium": 2, "low": 1}

_METRIC_LABELS: dict[str, str] = {
    "daily_gross_sales": "Revenue",
    "daily_gross_amount": "Revenue",
    "daily_transactions": "Orders",
    "daily_returns": "Returns",
    "daily_customers": "Customers",
    "daily_unique_customers": "Customers",
}


def _metric_label(metric: str) -> str:
    return _METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def pick_top_anomaly(
    alerts: list[AnomalyAlertResponse],
) -> AnomalyAlertResponse | None:
    """Select the most attention-worthy unsuppressed anomaly.

    Suppressed alerts never win the banner slot. Ties are broken by
    ``severity`` tier (critical > high > medium > low), then by absolute
    ``z_score`` (bigger deviation wins), then by most recent ``period``.
    """
    candidates = [a for a in alerts if not a.is_suppressed]
    if not candidates:
        return None

    def _sort_key(a: AnomalyAlertResponse) -> tuple[int, Decimal, str]:
        sev_rank = _SEVERITY_RANK.get(a.severity.lower(), 0)
        z = abs(Decimal(str(a.z_score))) if a.z_score is not None else Decimal("0")
        return (sev_rank, z, a.period.isoformat())

    return max(candidates, key=_sort_key)


def anomaly_to_top_insight(
    alert: AnomalyAlertResponse,
    *,
    now: datetime | None = None,
) -> TopInsight:
    """Project an anomaly alert onto the banner-ready card shape."""
    ref_now = now or datetime.now(UTC)
    label = _metric_label(alert.metric)

    actual = Decimal(str(alert.actual_value))
    expected = Decimal(str(alert.expected_value))

    # Title: "{metric} up/down N%" when expected > 0, else absolute.
    if expected > 0:
        delta_pct = ((actual - expected) / expected * Decimal("100")).quantize(Decimal("1"))
        direction_word = "up" if alert.direction.lower() in {"spike", "up"} else "down"
        sign = "+" if delta_pct >= 0 else ""
        title = f"{label} {direction_word} {sign}{delta_pct}%"
    else:
        verb = "spiked" if alert.direction.lower() in {"spike", "up"} else "dropped"
        title = f"{label} {verb} to {actual}"

    # Body: narrative with expected range.
    body_parts = [f"{label} on {alert.period.isoformat()} was {actual} vs expected {expected}."]
    if alert.z_score is not None:
        z = Decimal(str(alert.z_score)).quantize(Decimal("0.1"))
        body_parts.append(f"Z-score {z}.")
    body = " ".join(body_parts)

    # Expected impact: |actual - expected| for drops; None for spikes (not a loss).
    impact: Decimal | None = None
    if alert.direction.lower() in {"drop", "down"} and expected > 0:
        impact = (expected - actual).max(Decimal("0"))

    confidence = _SEVERITY_TO_CONFIDENCE.get(alert.severity.lower(), "info")

    return TopInsight(
        title=title,
        body=body,
        expected_impact_egp=impact,
        action_label="Investigate",
        action_target=f"/dashboard/anomalies/{alert.id}",
        confidence=confidence,
        generated_at=ref_now,
    )
