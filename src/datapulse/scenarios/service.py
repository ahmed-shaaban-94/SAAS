"""What-if scenario simulation service."""

from __future__ import annotations

from decimal import Decimal

from datapulse.logging import get_logger
from datapulse.scenarios.models import (
    AdjustmentParam,
    ChangeType,
    ImpactSummary,
    ScenarioInput,
    ScenarioResult,
    TimePoint,
)
from datapulse.scenarios.repository import ScenarioRepository

log = get_logger(__name__)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")

# Price elasticity of demand (inelastic — typical B2B/wholesale)
_PRICE_ELASTICITY = Decimal("0.5")


class ScenarioService:
    """Applies adjustments to baseline data and returns projected series."""

    def __init__(self, repo: ScenarioRepository) -> None:
        self._repo = repo

    def simulate(self, scenario: ScenarioInput) -> ScenarioResult:
        baseline = self._repo.get_monthly_baseline(scenario.months)
        if not baseline:
            return ScenarioResult(
                revenue_series=[],
                margin_series=[],
                revenue_impact=ImpactSummary(
                    baseline_total=_ZERO,
                    projected_total=_ZERO,
                    absolute_change=_ZERO,
                    percentage_change=0.0,
                ),
                margin_impact=ImpactSummary(
                    baseline_total=_ZERO,
                    projected_total=_ZERO,
                    absolute_change=_ZERO,
                    percentage_change=0.0,
                ),
            )

        # Build adjustment multipliers
        price_mult = _ONE
        volume_mult = _ONE
        cost_mult = _ONE

        for adj in scenario.adjustments:
            if adj.change_type == ChangeType.percentage:
                factor = _ONE + Decimal(str(adj.change_value)) / _HUNDRED
            else:
                factor = _ONE + Decimal(str(adj.change_value))

            if adj.parameter == AdjustmentParam.price:
                price_mult *= factor
                # Price elasticity: price increase reduces volume
                volume_mult *= _ONE - (factor - _ONE) * _PRICE_ELASTICITY
            elif adj.parameter == AdjustmentParam.volume:
                volume_mult *= factor
            elif adj.parameter == AdjustmentParam.cost:
                cost_mult *= factor

        revenue_series: list[TimePoint] = []
        margin_series: list[TimePoint] = []

        for row in baseline:
            base_rev = row["revenue"]
            base_cost = row["cost"]
            base_margin = base_rev - base_cost

            proj_rev = base_rev * price_mult * volume_mult
            proj_cost = base_cost * cost_mult * volume_mult
            proj_margin = proj_rev - proj_cost

            revenue_series.append(
                TimePoint(
                    month=row["month"],
                    baseline=base_rev,
                    projected=proj_rev,
                )
            )
            margin_series.append(
                TimePoint(
                    month=row["month"],
                    baseline=base_margin,
                    projected=proj_margin,
                )
            )

        return ScenarioResult(
            revenue_series=revenue_series,
            margin_series=margin_series,
            revenue_impact=self._summarize(revenue_series),
            margin_impact=self._summarize(margin_series),
        )

    @staticmethod
    def _summarize(series: list[TimePoint]) -> ImpactSummary:
        base_total = sum((p.baseline for p in series), Decimal("0"))
        proj_total = sum((p.projected for p in series), Decimal("0"))
        abs_change = proj_total - base_total
        pct_change = float(abs_change / base_total * _HUNDRED) if base_total else 0.0
        return ImpactSummary(
            baseline_total=base_total,
            projected_total=proj_total,
            absolute_change=abs_change,
            percentage_change=round(pct_change, 2),
        )
