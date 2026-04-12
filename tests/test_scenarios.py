"""Tests for what-if scenario simulation — service and repository."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from datapulse.scenarios.models import (
    Adjustment,
    AdjustmentParam,
    ChangeType,
    ScenarioInput,
    ScenarioResult,
)
from datapulse.scenarios.repository import ScenarioRepository
from datapulse.scenarios.service import ScenarioService


@pytest.fixture()
def mock_repo():
    return create_autospec(ScenarioRepository, instance=True)


@pytest.fixture()
def service(mock_repo):
    return ScenarioService(mock_repo)


BASELINE = [
    {"month": "2025-10", "revenue": Decimal("100000"), "cost": Decimal("60000"), "volume": 500},
    {"month": "2025-11", "revenue": Decimal("120000"), "cost": Decimal("72000"), "volume": 600},
]


class TestSimulatePercentageChange:
    def test_price_increase_10pct(self, service, mock_repo):
        mock_repo.get_monthly_baseline.return_value = BASELINE
        scenario = ScenarioInput(
            adjustments=[
                Adjustment(
                    parameter=AdjustmentParam.price,
                    change_type=ChangeType.percentage,
                    change_value=10.0,
                ),
            ],
            months=2,
        )
        result = service.simulate(scenario)
        assert isinstance(result, ScenarioResult)
        assert len(result.revenue_series) == 2
        # 10% price increase with 0.5 elasticity => volume factor = 1 - 0.1*0.5 = 0.95
        # Revenue = base * 1.10 * 0.95
        first = result.revenue_series[0]
        expected = Decimal("100000") * Decimal("1.1") * Decimal("0.95")
        assert first.projected == expected

    def test_empty_baseline_returns_zeros(self, service, mock_repo):
        mock_repo.get_monthly_baseline.return_value = []
        scenario = ScenarioInput(
            adjustments=[
                Adjustment(parameter=AdjustmentParam.volume, change_value=5.0),
            ],
        )
        result = service.simulate(scenario)
        assert result.revenue_series == []
        assert result.revenue_impact.baseline_total == Decimal("0")


class TestSimulateAbsoluteChange:
    def test_absolute_differs_from_percentage(self, service, mock_repo):
        """Absolute change must NOT divide by 100 like percentage does."""
        mock_repo.get_monthly_baseline.return_value = BASELINE

        pct_scenario = ScenarioInput(
            adjustments=[
                Adjustment(
                    parameter=AdjustmentParam.price,
                    change_type=ChangeType.percentage,
                    change_value=10.0,
                ),
            ],
            months=2,
        )
        abs_scenario = ScenarioInput(
            adjustments=[
                Adjustment(
                    parameter=AdjustmentParam.price,
                    change_type=ChangeType.absolute,
                    change_value=10.0,
                ),
            ],
            months=2,
        )

        pct_result = service.simulate(pct_scenario)
        abs_result = service.simulate(abs_scenario)

        # With the same change_value=10, percentage gives factor=1.10,
        # absolute gives factor=11.0 — they must differ.
        assert pct_result.revenue_series[0].projected != abs_result.revenue_series[0].projected

    def test_absolute_volume_increase(self, service, mock_repo):
        mock_repo.get_monthly_baseline.return_value = BASELINE
        scenario = ScenarioInput(
            adjustments=[
                Adjustment(
                    parameter=AdjustmentParam.volume,
                    change_type=ChangeType.absolute,
                    change_value=1.0,
                ),
            ],
            months=2,
        )
        result = service.simulate(scenario)
        # factor = 1 + 1.0 = 2.0 => revenue doubles
        first = result.revenue_series[0]
        assert first.projected == Decimal("100000") * Decimal("2")


class TestSimulateCostChange:
    def test_cost_increase_affects_margin(self, service, mock_repo):
        mock_repo.get_monthly_baseline.return_value = BASELINE
        scenario = ScenarioInput(
            adjustments=[
                Adjustment(
                    parameter=AdjustmentParam.cost,
                    change_type=ChangeType.percentage,
                    change_value=20.0,
                ),
            ],
            months=2,
        )
        result = service.simulate(scenario)
        first_margin = result.margin_series[0]
        base_margin = Decimal("100000") - Decimal("60000")
        proj_cost = Decimal("60000") * Decimal("1.2")
        expected_margin = Decimal("100000") - proj_cost
        assert first_margin.projected == expected_margin
        assert first_margin.baseline == base_margin


class TestImpactSummary:
    def test_percentage_change_calculation(self, service, mock_repo):
        mock_repo.get_monthly_baseline.return_value = BASELINE
        scenario = ScenarioInput(
            adjustments=[
                Adjustment(
                    parameter=AdjustmentParam.volume,
                    change_type=ChangeType.percentage,
                    change_value=50.0,
                ),
            ],
            months=2,
        )
        result = service.simulate(scenario)
        assert result.revenue_impact.percentage_change == 50.0
        assert result.revenue_impact.absolute_change > Decimal("0")


class TestRepositorySQL:
    def test_interval_uses_multiplication(self):
        """Verify the SQL uses INTERVAL '1 month' * :months, not INTERVAL ':months months'."""
        repo = ScenarioRepository.__new__(ScenarioRepository)
        # We can't run the SQL without a DB, but we can verify the source
        import inspect

        source = inspect.getsource(repo.get_monthly_baseline)
        assert "INTERVAL '1 month' * :months" in source
        assert "INTERVAL ':months" not in source
