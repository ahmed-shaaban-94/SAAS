"""Anomaly detection algorithms — Z-score and IQR."""

from __future__ import annotations

import statistics as _stats
from datetime import date
from decimal import Decimal

from datapulse.anomalies.models import AnomalyDetectionConfig, DetectedAnomaly
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class AnomalyDetector:
    """Statistical anomaly detection using Z-score and IQR methods."""

    def __init__(self, config: AnomalyDetectionConfig | None = None) -> None:
        self._config = config or AnomalyDetectionConfig()

    def detect_zscore(
        self,
        values: list[float],
        current: float,
        metric: str,
        period: date,
    ) -> DetectedAnomaly | None:
        """Detect anomaly using Z-score method.

        Returns an anomaly if |z| exceeds the low threshold (2.0).
        """

        if len(values) < self._config.min_data_points:
            return None

        mean = _stats.mean(values)
        stdev = _stats.stdev(values)
        if stdev == 0:
            return None

        z = (current - mean) / stdev
        abs_z = abs(z)

        if abs_z < self._config.low_z:
            return None

        severity = self._classify_severity(abs_z)
        direction = "spike" if z > 0 else "drop"

        lower = mean - self._config.medium_z * stdev
        upper = mean + self._config.medium_z * stdev

        return DetectedAnomaly(
            metric=metric,
            period=period,
            actual_value=Decimal(str(round(current, 4))),
            expected_value=Decimal(str(round(mean, 4))),
            lower_bound=Decimal(str(round(max(lower, 0), 4))),
            upper_bound=Decimal(str(round(upper, 4))),
            z_score=Decimal(str(round(z, 4))),
            severity=severity,
            direction=direction,
        )

    def detect_iqr(
        self,
        values: list[float],
        current: float,
        metric: str,
        period: date,
    ) -> DetectedAnomaly | None:
        """Detect anomaly using Interquartile Range method.

        Robust to outliers in the historical distribution.
        """
        if len(values) < self._config.min_data_points:
            return None

        sorted_vals = sorted(values)
        q1, _, q3 = _stats.quantiles(sorted_vals, n=4)
        iqr = q3 - q1
        if iqr == 0:
            return None

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        if lower <= current <= upper:
            return None

        # Compute pseudo z-score for severity classification
        median = _stats.median(values)
        mad = _stats.median([abs(v - median) for v in values])
        pseudo_z = abs(current - median) / (mad * 1.4826) if mad > 0 else 3.0

        severity = self._classify_severity(pseudo_z)
        direction = "spike" if current > upper else "drop"

        return DetectedAnomaly(
            metric=metric,
            period=period,
            actual_value=Decimal(str(round(current, 4))),
            expected_value=Decimal(str(round(_stats.mean(values), 4))),
            lower_bound=Decimal(str(round(max(lower, 0), 4))),
            upper_bound=Decimal(str(round(upper, 4))),
            z_score=Decimal(str(round(pseudo_z, 4))) if mad > 0 else None,
            severity=severity,
            direction=direction,
        )

    def detect_combined(
        self,
        values: list[float],
        current: float,
        metric: str,
        period: date,
    ) -> DetectedAnomaly | None:
        """Combined detection — flag only if BOTH Z-score and IQR agree.

        Reduces false positives by requiring consensus.
        """
        z_result = self.detect_zscore(values, current, metric, period)
        iqr_result = self.detect_iqr(values, current, metric, period)

        if z_result is not None and iqr_result is not None:
            # Use z-score result (more granular severity) when both agree
            return z_result

        return None

    def _classify_severity(self, abs_z: float) -> str:
        """Map absolute z-score to severity level."""
        if abs_z >= self._config.critical_z:
            return "critical"
        if abs_z >= self._config.high_z:
            return "high"
        if abs_z >= self._config.medium_z:
            return "medium"
        return "low"
