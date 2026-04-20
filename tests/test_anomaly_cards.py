"""Unit tests for anomaly → card projection (#508).

The mapper is intentionally pure (no DB, no clock) so every branch is
tested with explicit inputs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from datapulse.anomalies.cards import to_anomaly_card
from datapulse.anomalies.models import AnomalyAlertResponse


def _alert(**overrides) -> AnomalyAlertResponse:
    base = dict(
        id=1,
        metric="daily_gross_sales",
        period=date(2026, 4, 18),
        actual_value=Decimal("8200"),
        expected_value=Decimal("10000"),
        z_score=Decimal("-3.1"),
        severity="high",
        direction="drop",
    )
    base.update(overrides)
    return AnomalyAlertResponse(**base)


# ────────────────────────────────────────────────────────────────────────
# kind
# ────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("direction", "expected_kind"),
    [
        ("spike", "up"),
        ("up", "up"),
        ("drop", "down"),
        ("down", "down"),
        ("sideways", "info"),
    ],
)
def test_kind_maps_direction(direction, expected_kind):
    card = to_anomaly_card(_alert(direction=direction), today=date(2026, 4, 20))
    assert card.kind == expected_kind


def test_suppressed_alert_always_reports_info_kind():
    """Suppressed alerts aren't actionable — kind falls back to info."""
    alert = _alert(is_suppressed=True, suppression_reason="Eid holiday")
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert card.kind == "info"


# ────────────────────────────────────────────────────────────────────────
# confidence
# ────────────────────────────────────────────────────────────────────────


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
def test_confidence_maps_severity(severity, expected_confidence):
    card = to_anomaly_card(_alert(severity=severity), today=date(2026, 4, 20))
    assert card.confidence == expected_confidence


def test_suppressed_alert_reports_info_confidence():
    alert = _alert(is_suppressed=True, suppression_reason="Ramadan")
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert card.confidence == "info"


# ────────────────────────────────────────────────────────────────────────
# title
# ────────────────────────────────────────────────────────────────────────


def test_title_uses_delta_pct_when_expected_positive():
    alert = _alert(
        direction="drop",
        actual_value=Decimal("8200"),
        expected_value=Decimal("10000"),
    )
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    # (8200 - 10000) / 10000 * 100 = -18
    assert card.title == "Revenue down -18%"


def test_title_uses_plus_sign_on_positive_delta():
    alert = _alert(
        direction="spike",
        actual_value=Decimal("12000"),
        expected_value=Decimal("10000"),
    )
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert card.title == "Revenue up +20%"


def test_title_falls_back_to_absolute_when_expected_zero():
    """Expected=0 means no pct delta is meaningful — use absolute value."""
    alert = _alert(
        metric="daily_returns",
        direction="spike",
        actual_value=Decimal("15"),
        expected_value=Decimal("0"),
    )
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert card.title == "Returns spiked to 15"


def test_title_marks_suppressed_alerts():
    alert = _alert(is_suppressed=True, suppression_reason="Eid holiday")
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert card.title == "Revenue flagged (suppressed)"


def test_title_prettifies_unknown_metric():
    alert = _alert(
        metric="avg_basket_size",
        direction="drop",
        actual_value=Decimal("90"),
        expected_value=Decimal("100"),
    )
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    # underscore → space, title-cased.
    assert card.title.startswith("Avg Basket Size")


# ────────────────────────────────────────────────────────────────────────
# body
# ────────────────────────────────────────────────────────────────────────


def test_body_includes_actual_expected_and_z_score():
    alert = _alert(z_score=Decimal("-3.14"))
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert "Revenue on 2026-04-18 was 8200 (expected 10000)." in card.body
    assert "z=-3.1" in card.body


def test_body_omits_z_when_missing():
    alert = _alert(z_score=None)
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert "z=" not in card.body


def test_body_for_suppressed_mentions_reason():
    alert = _alert(is_suppressed=True, suppression_reason="Ramadan")
    card = to_anomaly_card(alert, today=date(2026, 4, 20))
    assert "Suppressed on 2026-04-18" in card.body
    assert "Ramadan" in card.body


# ────────────────────────────────────────────────────────────────────────
# time_ago
# ────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("period", "today", "expected"),
    [
        (date(2026, 4, 20), date(2026, 4, 20), "today"),
        (date(2026, 4, 19), date(2026, 4, 20), "1d ago"),
        (date(2026, 4, 18), date(2026, 4, 20), "2d ago"),
        (date(2026, 4, 14), date(2026, 4, 20), "6d ago"),
        (date(2026, 4, 13), date(2026, 4, 20), "1w ago"),
        (date(2026, 4, 6), date(2026, 4, 20), "2w ago"),
        (date(2026, 3, 20), date(2026, 4, 20), "1mo ago"),
        (date(2026, 1, 20), date(2026, 4, 20), "3mo ago"),
        (date(2026, 4, 21), date(2026, 4, 20), "today"),  # future → treated as today
    ],
)
def test_time_ago_buckets(period, today, expected):
    alert = _alert(period=period)
    card = to_anomaly_card(alert, today=today)
    assert card.time_ago == expected


# ────────────────────────────────────────────────────────────────────────
# id passthrough
# ────────────────────────────────────────────────────────────────────────


def test_card_preserves_alert_id():
    card = to_anomaly_card(_alert(id=42), today=date(2026, 4, 20))
    assert card.id == 42
