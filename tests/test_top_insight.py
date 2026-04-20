"""Tests for the top-insight builder (issue #510)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from datapulse.ai_light.top_insight import build_top_insight
from datapulse.anomalies.models import AnomalyAlertResponse


def _alert(**overrides) -> AnomalyAlertResponse:
    base = {
        "id": 1,
        "metric": "daily_gross_sales",
        "period": date(2026, 4, 20),
        "actual_value": Decimal("80000"),
        "expected_value": Decimal("100000"),
        "z_score": Decimal("-2.5"),
        "severity": "medium",
        "direction": "drop",
        "is_suppressed": False,
        "suppression_reason": None,
        "acknowledged": False,
    }
    base.update(overrides)
    return AnomalyAlertResponse(**base)


def test_build_top_insight_returns_none_when_empty():
    assert build_top_insight([]) is None


def test_build_top_insight_skips_suppressed_alerts():
    alerts = [
        _alert(id=1, is_suppressed=True, suppression_reason="Eid"),
    ]
    assert build_top_insight(alerts) is None


def test_build_top_insight_prefers_critical_over_high():
    alerts = [
        _alert(id=1, severity="high", z_score=Decimal("-3.0")),
        _alert(id=2, severity="critical", z_score=Decimal("-2.5")),
    ]
    insight = build_top_insight(alerts, today=date(2026, 4, 20))
    assert insight is not None
    # Critical wins on severity even with lower z-score magnitude.
    assert insight.action_target == "/dashboard/v3/anomalies/2"
    assert insight.confidence == "high"


def test_build_top_insight_breaks_tie_by_z_score_magnitude():
    alerts = [
        _alert(id=1, severity="high", z_score=Decimal("-2.5")),
        _alert(id=2, severity="high", z_score=Decimal("-3.9")),
    ]
    insight = build_top_insight(alerts, today=date(2026, 4, 20))
    assert insight is not None
    assert insight.action_target == "/dashboard/v3/anomalies/2"


def test_build_top_insight_populates_title_and_body():
    insight = build_top_insight(
        [_alert(id=7, severity="high", direction="drop")],
        today=date(2026, 4, 20),
    )
    assert insight is not None
    assert "Daily revenue" in insight.title
    assert insight.body  # non-empty
    assert insight.action_label == "Investigate"
    assert insight.generated_at == date(2026, 4, 20)


def test_build_top_insight_action_target_links_to_v3():
    insight = build_top_insight(
        [_alert(id=42)],
        today=date(2026, 4, 20),
    )
    assert insight is not None
    assert insight.action_target == "/dashboard/v3/anomalies/42"


def test_build_top_insight_handles_missing_z_score():
    alerts = [
        _alert(id=1, severity="high", z_score=None),
        _alert(id=2, severity="high", z_score=Decimal("-3.0")),
    ]
    insight = build_top_insight(alerts, today=date(2026, 4, 20))
    assert insight is not None
    # z=-3.0 outranks z=None which is treated as 0.
    assert insight.action_target == "/dashboard/v3/anomalies/2"
