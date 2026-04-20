"""Tests for the anomaly card adapter and AnomalyService.get_cards (issue #508)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.anomalies.cards import to_card
from datapulse.anomalies.models import AnomalyAlertResponse
from datapulse.anomalies.repository import AnomalyRepository
from datapulse.anomalies.service import AnomalyService


def _alert(**overrides) -> AnomalyAlertResponse:
    base = {
        "id": 42,
        "metric": "daily_gross_sales",
        "period": date(2026, 4, 18),
        "actual_value": Decimal("82000"),
        "expected_value": Decimal("100000"),
        "z_score": Decimal("-2.7"),
        "severity": "high",
        "direction": "drop",
        "is_suppressed": False,
        "suppression_reason": None,
        "acknowledged": False,
    }
    base.update(overrides)
    return AnomalyAlertResponse(**base)


# ------------------------------------------------------------------
# to_card adapter
# ------------------------------------------------------------------


def test_to_card_maps_drop_to_down_kind():
    card = to_card(_alert(direction="drop"), today=date(2026, 4, 20))
    assert card.kind == "down"


def test_to_card_maps_spike_to_up_kind():
    card = to_card(_alert(direction="spike"), today=date(2026, 4, 20))
    assert card.kind == "up"


def test_to_card_suppressed_collapses_to_info():
    card = to_card(
        _alert(is_suppressed=True, suppression_reason="Eid al-Fitr"),
        today=date(2026, 4, 20),
    )
    assert card.kind == "info"
    assert card.confidence == "info"
    assert "suppressed" in card.body


def test_to_card_severity_to_confidence_mapping():
    assert to_card(_alert(severity="critical"), today=date(2026, 4, 20)).confidence == "high"
    assert to_card(_alert(severity="high"), today=date(2026, 4, 20)).confidence == "high"
    assert to_card(_alert(severity="medium"), today=date(2026, 4, 20)).confidence == "medium"
    assert to_card(_alert(severity="low"), today=date(2026, 4, 20)).confidence == "low"


def test_to_card_renders_percent_in_title():
    # actual=82k, expected=100k -> 18% drop
    card = to_card(_alert(), today=date(2026, 4, 20))
    assert "Daily revenue" in card.title
    assert "down" in card.title
    assert "18" in card.title  # "18.0%"


def test_to_card_handles_zero_expected():
    card = to_card(
        _alert(actual_value=Decimal("5"), expected_value=Decimal("0")),
        today=date(2026, 4, 20),
    )
    # No percent to render -> title is just the metric label
    assert card.title == "Daily revenue"


def test_to_card_time_ago_today():
    assert to_card(_alert(period=date(2026, 4, 20)), today=date(2026, 4, 20)).time_ago == "today"


def test_to_card_time_ago_single_day():
    assert to_card(_alert(period=date(2026, 4, 19)), today=date(2026, 4, 20)).time_ago == "1d ago"


def test_to_card_time_ago_multi_day():
    assert to_card(_alert(period=date(2026, 4, 15)), today=date(2026, 4, 20)).time_ago == "5d ago"


def test_to_card_id_preserved():
    assert to_card(_alert(id=99), today=date(2026, 4, 20)).id == 99


def test_to_card_body_includes_z_score_when_present():
    body = to_card(_alert(z_score=Decimal("-2.7")), today=date(2026, 4, 20)).body
    assert "z=" in body


def test_to_card_body_omits_z_score_when_none():
    body = to_card(_alert(z_score=None), today=date(2026, 4, 20)).body
    assert "z=" not in body


# ------------------------------------------------------------------
# AnomalyService.get_cards
# ------------------------------------------------------------------


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock(spec=AnomalyRepository)


@pytest.fixture()
def service(mock_repo: MagicMock) -> AnomalyService:
    return AnomalyService(session=MagicMock(), repo=mock_repo)


def test_get_cards_projects_each_alert(service: AnomalyService, mock_repo: MagicMock):
    mock_repo.get_active_alerts.return_value = [_alert(id=1), _alert(id=2)]
    cards = service.get_cards(limit=10)
    assert [c.id for c in cards] == [1, 2]
    mock_repo.get_active_alerts.assert_called_once_with(limit=10)


def test_get_cards_forwards_limit(service: AnomalyService, mock_repo: MagicMock):
    mock_repo.get_active_alerts.return_value = []
    service.get_cards(limit=5)
    mock_repo.get_active_alerts.assert_called_once_with(limit=5)


def test_get_cards_empty_returns_empty_list(service: AnomalyService, mock_repo: MagicMock):
    mock_repo.get_active_alerts.return_value = []
    assert service.get_cards() == []
