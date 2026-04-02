"""Tests for targets module — service, repository, and models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from pydantic import ValidationError

from datapulse.targets.models import (
    AlertConfigCreate,
    AlertConfigResponse,
    AlertLogResponse,
    TargetCreate,
    TargetResponse,
    TargetSummary,
    TargetVsActual,
)
from datapulse.targets.repository import TargetsRepository
from datapulse.targets.service import TargetsService

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> TargetsRepository:
    return TargetsRepository(mock_session)


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(TargetsRepository, instance=True)


@pytest.fixture()
def service(mock_repo: MagicMock) -> TargetsService:
    return TargetsService(mock_repo)


NOW = datetime(2025, 6, 15, 12, 0, 0)


def _target_row(**overrides):
    base = {
        "id": 1,
        "target_type": "revenue",
        "granularity": "monthly",
        "period": "2025-06",
        "target_value": Decimal("100000"),
        "entity_type": None,
        "entity_key": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return base


def _alert_config_row(**overrides):
    base = {
        "id": 1,
        "alert_name": "Low revenue",
        "metric": "daily_revenue",
        "condition": "below",
        "threshold": Decimal("5000"),
        "entity_type": None,
        "entity_key": None,
        "enabled": True,
        "notify_channels": ["dashboard"],
        "created_at": NOW,
    }
    base.update(overrides)
    return base


def _alert_log_row(**overrides):
    base = {
        "id": 1,
        "alert_config_id": 1,
        "alert_name": "Low revenue",
        "fired_at": NOW,
        "metric_value": Decimal("3500"),
        "threshold_value": Decimal("5000"),
        "message": "Daily revenue below threshold",
        "acknowledged": False,
    }
    base.update(overrides)
    return base


# ── Model Tests ───────────────────────────────────────────────────────


class TestTargetModels:
    def test_target_create_minimal(self):
        t = TargetCreate(
            target_type="revenue",
            granularity="monthly",
            period="2025-06",
            target_value=Decimal("100000"),
        )
        assert t.target_type == "revenue"
        assert t.entity_type is None

    def test_target_response_frozen(self):
        t = TargetResponse(**_target_row())
        with pytest.raises((TypeError, AttributeError, ValidationError)):
            t.target_type = "transactions"  # type: ignore[misc]

    def test_target_vs_actual(self):
        tva = TargetVsActual(
            period="2025-06",
            target_value=Decimal("100000"),
            actual_value=Decimal("95000"),
            variance=Decimal("-5000"),
            achievement_pct=Decimal("95.00"),
        )
        assert tva.variance == Decimal("-5000")

    def test_target_summary_defaults(self):
        ts = TargetSummary(monthly_targets=[])
        assert ts.ytd_target == Decimal("0")
        assert ts.ytd_actual == Decimal("0")

    def test_alert_config_create_defaults(self):
        a = AlertConfigCreate(
            alert_name="Test",
            metric="revenue",
            condition="below",
            threshold=Decimal("1000"),
        )
        assert a.enabled is True
        assert a.notify_channels == ["dashboard"]

    def test_alert_log_response(self):
        al = AlertLogResponse(**_alert_log_row())
        assert al.acknowledged is False


# ── Repository Tests ──────────────────────────────────────────────────


class TestTargetsRepository:
    def test_create_target(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchone.return_value = (
            _target_row()
        )
        data = TargetCreate(
            target_type="revenue",
            granularity="monthly",
            period="2025-06",
            target_value=Decimal("100000"),
        )
        result = repo.create_target(data)
        assert isinstance(result, TargetResponse)
        assert result.id == 1
        mock_session.execute.assert_called_once()

    def test_list_targets_no_filters(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchall.return_value = [
            _target_row(),
            _target_row(id=2, period="2025-07"),
        ]
        result = repo.list_targets()
        assert len(result) == 2

    def test_list_targets_with_filters(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchall.return_value = []
        result = repo.list_targets(
            target_type="revenue", granularity="monthly", period_prefix="2025"
        )
        assert result == []
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["target_type"] == "revenue"
        assert params["granularity"] == "monthly"
        assert params["period_prefix"] == "2025"

    def test_delete_target_found(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 1
        assert repo.delete_target(1) is True

    def test_delete_target_not_found(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 0
        assert repo.delete_target(999) is False

    def test_get_target_vs_actual_with_data(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchall.return_value = [
            ("2025-01", Decimal("100000"), Decimal("95000")),
            ("2025-02", Decimal("100000"), Decimal("110000")),
        ]
        result = repo.get_target_vs_actual(2025)
        assert isinstance(result, TargetSummary)
        assert len(result.monthly_targets) == 2
        assert result.ytd_target == Decimal("200000")
        assert result.ytd_actual == Decimal("205000")

    def test_get_target_vs_actual_empty(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.fetchall.return_value = []
        result = repo.get_target_vs_actual(2025)
        assert result.monthly_targets == []
        assert result.ytd_achievement_pct == Decimal("0")

    def test_get_target_vs_actual_zero_target(
        self, repo: TargetsRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value.fetchall.return_value = [
            ("2025-01", Decimal("0"), Decimal("50000")),
        ]
        result = repo.get_target_vs_actual(2025)
        assert result.monthly_targets[0].achievement_pct == Decimal("0")

    def test_list_alert_configs(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchall.return_value = [
            _alert_config_row()
        ]
        result = repo.list_alert_configs()
        assert len(result) == 1
        assert isinstance(result[0], AlertConfigResponse)

    def test_create_alert_config(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchone.return_value = (
            _alert_config_row()
        )
        data = AlertConfigCreate(
            alert_name="Low revenue",
            metric="daily_revenue",
            condition="below",
            threshold=Decimal("5000"),
        )
        result = repo.create_alert_config(data)
        assert isinstance(result, AlertConfigResponse)

    def test_update_alert_config_found(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchone.return_value = (
            _alert_config_row(enabled=False)
        )
        result = repo.update_alert_config(1, enabled=False)
        assert result is not None
        assert result.enabled is False

    def test_update_alert_config_not_found(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchone.return_value = None
        result = repo.update_alert_config(999, enabled=True)
        assert result is None

    def test_list_alert_logs(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.mappings.return_value.fetchall.return_value = [
            _alert_log_row()
        ]
        result = repo.list_alert_logs(limit=10)
        assert len(result) == 1

    def test_list_alert_logs_unacknowledged_only(
        self, repo: TargetsRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value.mappings.return_value.fetchall.return_value = []
        result = repo.list_alert_logs(unacknowledged_only=True)
        assert result == []

    def test_acknowledge_alert_found(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 1
        assert repo.acknowledge_alert(1) is True

    def test_acknowledge_alert_not_found(self, repo: TargetsRepository, mock_session: MagicMock):
        mock_session.execute.return_value.rowcount = 0
        assert repo.acknowledge_alert(999) is False


# ── Service Tests ─────────────────────────────────────────────────────


class TestTargetsService:
    def test_create_target(self, service: TargetsService, mock_repo: MagicMock):
        expected = TargetResponse(**_target_row())
        mock_repo.create_target.return_value = expected
        data = TargetCreate(
            target_type="revenue",
            granularity="monthly",
            period="2025-06",
            target_value=Decimal("100000"),
        )
        result = service.create_target(data)
        assert result == expected
        mock_repo.create_target.assert_called_once_with(data)

    def test_list_targets_passes_period_as_prefix(
        self, service: TargetsService, mock_repo: MagicMock
    ):
        mock_repo.list_targets.return_value = []
        service.list_targets(period="2025")
        mock_repo.list_targets.assert_called_once_with(
            target_type=None, granularity=None, period_prefix="2025"
        )

    def test_delete_target(self, service: TargetsService, mock_repo: MagicMock):
        mock_repo.delete_target.return_value = True
        assert service.delete_target(1) is True

    def test_get_target_summary(self, service: TargetsService, mock_repo: MagicMock):
        expected = TargetSummary(monthly_targets=[])
        mock_repo.get_target_vs_actual.return_value = expected
        result = service.get_target_summary(2025)
        assert result == expected

    def test_list_alert_configs(self, service: TargetsService, mock_repo: MagicMock):
        mock_repo.list_alert_configs.return_value = []
        assert service.list_alert_configs() == []

    def test_create_alert_config(self, service: TargetsService, mock_repo: MagicMock):
        expected = AlertConfigResponse(**_alert_config_row())
        mock_repo.create_alert_config.return_value = expected
        data = AlertConfigCreate(
            alert_name="Low revenue",
            metric="daily_revenue",
            condition="below",
            threshold=Decimal("5000"),
        )
        assert service.create_alert_config(data) == expected

    def test_toggle_alert(self, service: TargetsService, mock_repo: MagicMock):
        expected = AlertConfigResponse(**_alert_config_row(enabled=False))
        mock_repo.update_alert_config.return_value = expected
        result = service.toggle_alert(1, enabled=False)
        assert result == expected

    def test_toggle_alert_not_found(self, service: TargetsService, mock_repo: MagicMock):
        mock_repo.update_alert_config.return_value = None
        assert service.toggle_alert(999, True) is None

    def test_get_active_alerts(self, service: TargetsService, mock_repo: MagicMock):
        mock_repo.list_alert_logs.return_value = []
        result = service.get_active_alerts(limit=10, unacknowledged_only=True)
        assert result == []
        mock_repo.list_alert_logs.assert_called_once_with(limit=10, unacknowledged_only=True)

    def test_acknowledge_alert(self, service: TargetsService, mock_repo: MagicMock):
        mock_repo.acknowledge_alert.return_value = True
        assert service.acknowledge_alert(1) is True
