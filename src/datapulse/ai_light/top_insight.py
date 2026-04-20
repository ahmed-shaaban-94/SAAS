"""Top-insight builder — pick the single most important anomaly for the AI banner.

Kept as a pure function so the route can stay thin and the ordering logic
is trivially testable. Called by the ``/ai-light/top-insight`` endpoint
(issue #510).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from datapulse.ai_light.models import TopInsight
from datapulse.anomalies.cards import to_card
from datapulse.anomalies.models import AnomalyAlertResponse

# Lower index = higher priority when picking the headline alert.
_SEVERITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def _severity_key(alert: AnomalyAlertResponse) -> tuple[int, Decimal]:
    severity_rank = _SEVERITY_ORDER.get(alert.severity, 99)
    z = abs(alert.z_score) if alert.z_score is not None else Decimal(0)
    # Negate so larger z-scores sort first (min-style tuple comparison).
    return (severity_rank, -z)


def build_top_insight(
    alerts: list[AnomalyAlertResponse],
    today: date | None = None,
) -> TopInsight | None:
    """Pick the most severe unsuppressed alert and project it to a TopInsight.

    Returns None when there are no eligible alerts — the caller should
    translate that into a 204 so the banner hides cleanly.
    """
    eligible = [a for a in alerts if not a.is_suppressed]
    if not eligible:
        return None

    alert = min(eligible, key=_severity_key)
    card = to_card(alert, today=today)

    return TopInsight(
        title=card.title,
        body=card.body,
        action_label="Investigate",
        action_target=f"/dashboard/v3/anomalies/{alert.id}",
        confidence=card.confidence,
        generated_at=today or date.today(),
    )
