"""Unit tests for the top-insight banner (#510)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from datapulse.ai_light.top_insight import (
    anomaly_to_top_insight,
    pick_top_anomaly,
)
from datapulse.anomalies.models import AnomalyAlertResponse


def _alert(**overrides) -> AnomalyAlertResponse:
    base = dict(
        id=1,
        metric="daily_gross_sales",
        period=date(2026, 4, 18),
        actual_value=Decimal("82000"),
        expected_value=Decimal("100000"),
        z_score=Decimal("-3.1"),
        severity="high",
        direction="drop",
    )
    base.update(overrides)
    return AnomalyAlertResponse(**base)


# ────────────────────────────────────────────────────────────────────────
# pick_top_anomaly
# ────────────────────────────────────────────────────────────────────────


def test_pick_top_returns_none_when_list_empty():
    assert pick_top_anomaly([]) is None


def test_pick_top_skips_suppressed():
    alerts = [
        _alert(id=1, severity="critical", is_suppressed=True, suppression_reason="Eid"),
    ]
    assert pick_top_anomaly(alerts) is None


def test_pick_top_prefers_critical_over_lower_severity():
    alerts = [
        _alert(id=1, severity="medium", z_score=Decimal("-5")),
        _alert(id=2, severity="critical", z_score=Decimal("-2")),
        _alert(id=3, severity="low", z_score=Decimal("-8")),
    ]
    top = pick_top_anomaly(alerts)
    assert top is not None
    assert top.id == 2


def test_pick_top_breaks_ties_on_absolute_z_score():
    alerts = [
        _alert(id=1, severity="high", z_score=Decimal("-3.1")),
        _alert(id=2, severity="high", z_score=Decimal("4.8")),
        _alert(id=3, severity="high", z_score=Decimal("-2.5")),
    ]
    top = pick_top_anomaly(alerts)
    assert top is not None
    assert top.id == 2  # |4.8| > |3.1| > |2.5|


def test_pick_top_handles_null_z_score():
    """An alert with no z_score must still be comparable — treated as 0."""
    alerts = [
        _alert(id=1, severity="high", z_score=None),
        _alert(id=2, severity="high", z_score=Decimal("-1")),
    ]
    top = pick_top_anomaly(alerts)
    assert top is not None
    assert top.id == 2


def test_pick_top_handles_mixed_suppressed_and_active():
    alerts = [
        _alert(id=1, severity="critical", is_suppressed=True, suppression_reason="Eid"),
        _alert(id=2, severity="medium"),
    ]
    top = pick_top_anomaly(alerts)
    assert top is not None
    assert top.id == 2


# ────────────────────────────────────────────────────────────────────────
# anomaly_to_top_insight — card mapping
# ────────────────────────────────────────────────────────────────────────


_NOW = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)


def test_drop_with_positive_expected_emits_delta_pct_title():
    alert = _alert(
        direction="drop",
        actual_value=Decimal("82000"),
        expected_value=Decimal("100000"),
    )
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.title == "Revenue down -18%"


def test_spike_emits_positive_delta():
    alert = _alert(
        direction="spike",
        actual_value=Decimal("120000"),
        expected_value=Decimal("100000"),
    )
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.title == "Revenue up +20%"


def test_zero_expected_falls_back_to_absolute_value():
    alert = _alert(
        metric="daily_returns",
        direction="spike",
        actual_value=Decimal("25"),
        expected_value=Decimal("0"),
    )
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.title == "Returns spiked to 25"


def test_body_includes_actual_expected_and_z_score():
    alert = _alert(z_score=Decimal("-3.14"))
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert "Revenue on 2026-04-18 was 82000 vs expected 100000." in card.body
    assert "Z-score -3.1." in card.body


def test_body_omits_z_when_absent():
    alert = _alert(z_score=None)
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert "Z-score" not in card.body


def test_expected_impact_populated_for_drops_only():
    alert = _alert(
        direction="drop",
        actual_value=Decimal("82000"),
        expected_value=Decimal("100000"),
    )
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.expected_impact_egp == Decimal("18000")


def test_expected_impact_none_for_spikes():
    alert = _alert(
        direction="spike",
        actual_value=Decimal("120000"),
        expected_value=Decimal("100000"),
    )
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.expected_impact_egp is None


def test_expected_impact_clamped_to_zero_when_actual_exceeds_expected_on_drop():
    """A 'drop' alert whose actual > expected shouldn't produce a negative impact."""
    alert = _alert(
        direction="drop",
        actual_value=Decimal("110000"),
        expected_value=Decimal("100000"),
    )
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.expected_impact_egp == Decimal("0")


@pytest.mark.parametrize(
    ("severity", "expected_confidence"),
    [
        ("critical", "high"),
        ("high", "high"),
        ("medium", "medium"),
        ("low", "low"),
        ("unknown", "info"),
    ],
)
def test_confidence_mirrors_severity(severity, expected_confidence):
    alert = _alert(severity=severity)
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.confidence == expected_confidence


def test_action_target_deep_links_to_anomaly_detail():
    alert = _alert(id=142)
    card = anomaly_to_top_insight(alert, now=_NOW)
    assert card.action_label == "Investigate"
    assert card.action_target == "/dashboard/anomalies/142"


def test_generated_at_uses_supplied_clock():
    card = anomaly_to_top_insight(_alert(), now=_NOW)
    assert card.generated_at == _NOW
