"""Dedicated tests for AILightService._build_change_narrative_text."""

from __future__ import annotations

from decimal import Decimal

from datapulse.ai_light.models import ChangeDelta
from datapulse.ai_light.service import AILightService


class TestBuildChangeNarrativeText:
    """Covers _build_change_narrative_text across all meaningful scenarios."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _delta(
        metric: str,
        current: str,
        previous: str,
        change_pct: str,
        direction: str,
    ) -> ChangeDelta:
        return ChangeDelta(
            metric=metric,
            current_value=Decimal(current),
            previous_value=Decimal(previous),
            change_pct=Decimal(change_pct),
            direction=direction,
        )

    # ------------------------------------------------------------------
    # 1. Single metric — direction "up" (richer assertions than existing test)
    # ------------------------------------------------------------------

    def test_single_metric_up(self) -> None:
        delta = self._delta("Net Sales", "120", "100", "20", "up")
        result = AILightService._build_change_narrative_text([delta])

        assert result.startswith("Period comparison: ")
        assert result.endswith(".")
        assert "Net Sales" in result
        assert "up" in result
        assert "20.0%" in result
        assert "120" in result

    # ------------------------------------------------------------------
    # 2. Single metric — direction "down" (negative change)
    # ------------------------------------------------------------------

    def test_single_metric_down(self) -> None:
        delta = self._delta("Revenue", "80", "100", "-20", "down")
        result = AILightService._build_change_narrative_text([delta])

        assert "Revenue" in result
        assert "down" in result
        # abs(-20) → "20.0%"
        assert "20.0%" in result
        # current_value formatted as integer
        assert "80" in result

    # ------------------------------------------------------------------
    # 3. Direction "flat" — zero change_pct
    # ------------------------------------------------------------------

    def test_single_metric_flat(self) -> None:
        delta = self._delta("Margin", "100", "100", "0", "flat")
        result = AILightService._build_change_narrative_text([delta])

        assert "Margin" in result
        assert "flat" in result
        assert "0.0%" in result

    # ------------------------------------------------------------------
    # 4. Multiple metrics — all appear in output
    # ------------------------------------------------------------------

    def test_multiple_metrics(self) -> None:
        deltas = [
            self._delta("Net Sales", "120", "100", "20", "up"),
            self._delta("Orders", "90", "100", "-10", "down"),
            self._delta("Margin", "50", "50", "0", "flat"),
        ]
        result = AILightService._build_change_narrative_text(deltas)

        assert result.startswith("Period comparison: ")
        assert result.endswith(".")
        assert "Net Sales" in result
        assert "Orders" in result
        assert "Margin" in result
        # Separator between parts
        assert ";" in result

    # ------------------------------------------------------------------
    # 5. Empty deltas list
    # ------------------------------------------------------------------

    def test_empty_deltas(self) -> None:
        result = AILightService._build_change_narrative_text([])

        assert result == "Period comparison: ."

    # ------------------------------------------------------------------
    # 6. Large values — comma-formatted with :,.0f
    # ------------------------------------------------------------------

    def test_large_value_comma_formatting(self) -> None:
        delta = self._delta("Gross Revenue", "1234567.89", "1000000", "23.456789", "up")
        result = AILightService._build_change_narrative_text([delta])

        # :,.0f rounds 1234567.89 → "1,234,568"
        assert "1,234,568" in result
        assert "Gross Revenue" in result

    # ------------------------------------------------------------------
    # 7. Zero current_value — no ZeroDivisionError
    # ------------------------------------------------------------------

    def test_zero_current_value(self) -> None:
        delta = self._delta("Refunds", "0", "100", "-100", "down")
        # Must not raise
        result = AILightService._build_change_narrative_text([delta])

        assert "Refunds" in result
        assert "0" in result

    # ------------------------------------------------------------------
    # 8. Negative current_value — returns/refunds scenario
    # ------------------------------------------------------------------

    def test_negative_current_value(self) -> None:
        delta = self._delta("Net Returns", "-500", "0", "-100", "down")
        result = AILightService._build_change_narrative_text([delta])

        assert "Net Returns" in result
        # :,.0f of -500.0 → "-500"
        assert "-500" in result
