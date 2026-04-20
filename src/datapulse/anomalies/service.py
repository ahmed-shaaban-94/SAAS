"""Anomaly detection service — orchestrates detection, suppression, persistence."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.anomalies.calendar import is_holiday_or_event
from datapulse.anomalies.cards import to_anomaly_card
from datapulse.anomalies.detector import AnomalyDetector
from datapulse.anomalies.models import (
    AnomalyAlertResponse,
    AnomalyCard,
    AnomalyDetectionConfig,
    AnomalyRunResult,
    DetectedAnomaly,
)
from datapulse.anomalies.repository import AnomalyRepository
from datapulse.logging import get_logger

log = get_logger(__name__)

# Metrics to check from metrics_summary
_METRICS = [
    ("daily_gross_amount", "daily_gross_sales"),
    ("daily_transactions", "daily_transactions"),
    ("daily_returns", "daily_returns"),
    ("daily_unique_customers", "daily_customers"),
]


class AnomalyService:
    """Detect anomalies in daily metrics and manage alerts."""

    def __init__(
        self,
        session: Session,
        repo: AnomalyRepository | None = None,
        config: AnomalyDetectionConfig | None = None,
    ) -> None:
        self._session = session
        self._repo = repo or AnomalyRepository(session)
        self._config = config or AnomalyDetectionConfig()
        self._detector = AnomalyDetector(self._config)

    def run_detection(self, target_date: date | None = None) -> AnomalyRunResult:
        """Run anomaly detection on the latest daily metrics.

        Queries the last `lookback_days` of metrics_summary, runs combined
        Z-score + IQR detection on each metric, suppresses holidays, and
        saves results.
        """
        if target_date is None:
            # Get the most recent date in metrics_summary
            row = self._session.execute(
                text("SELECT MAX(full_date) FROM public_marts.metrics_summary")
            ).scalar()
            if row is None:
                return AnomalyRunResult(
                    total_checked=0, anomalies_found=0, suppressed=0, alerts_saved=0
                )
            target_date = row

        lookback_start = target_date - timedelta(days=self._config.lookback_days)

        log.info(
            "anomaly_detection_start",
            target_date=str(target_date),
            lookback=self._config.lookback_days,
        )

        # Fetch historical + current metrics
        stmt = text("""
            SELECT full_date, daily_gross_amount, daily_transactions,
                   daily_returns, daily_unique_customers
            FROM public_marts.metrics_summary
            WHERE full_date BETWEEN :start AND :end
            ORDER BY full_date
        """)
        rows = self._session.execute(stmt, {"start": lookback_start, "end": target_date}).fetchall()

        if len(rows) < self._config.min_data_points:
            log.warning("anomaly_insufficient_data", count=len(rows))
            return AnomalyRunResult(
                total_checked=0, anomalies_found=0, suppressed=0, alerts_saved=0
            )

        total_checked = 0
        anomalies: list[DetectedAnomaly] = []

        # Current = last row, history = all rows except last
        current_row = rows[-1]
        history_rows = rows[:-1]

        for col_idx, (_col_name, metric_label) in enumerate(_METRICS, start=1):
            history_values = [float(r[col_idx]) for r in history_rows if r[col_idx] is not None]
            current_value = float(current_row[col_idx]) if current_row[col_idx] is not None else 0.0

            if len(history_values) < self._config.min_data_points:
                continue

            total_checked += 1
            anomaly = self._detector.detect_combined(
                history_values, current_value, metric_label, target_date
            )

            if anomaly is not None:
                # Check for holiday suppression
                is_event, event_name = is_holiday_or_event(target_date)
                if is_event:
                    anomaly = DetectedAnomaly(
                        metric=anomaly.metric,
                        period=anomaly.period,
                        actual_value=anomaly.actual_value,
                        expected_value=anomaly.expected_value,
                        lower_bound=anomaly.lower_bound,
                        upper_bound=anomaly.upper_bound,
                        z_score=anomaly.z_score,
                        severity=anomaly.severity,
                        direction=anomaly.direction,
                        is_suppressed=True,
                        suppression_reason=event_name,
                    )
                anomalies.append(anomaly)

        suppressed = sum(1 for a in anomalies if a.is_suppressed)
        alerts_saved = self._repo.save_alerts(anomalies)

        log.info(
            "anomaly_detection_complete",
            total_checked=total_checked,
            anomalies_found=len(anomalies),
            suppressed=suppressed,
            saved=alerts_saved,
        )

        return AnomalyRunResult(
            total_checked=total_checked,
            anomalies_found=len(anomalies),
            suppressed=suppressed,
            alerts_saved=alerts_saved,
        )

    def get_active_alerts(self, limit: int = 20) -> list[AnomalyAlertResponse]:
        """Return unacknowledged, unsuppressed alerts."""
        return self._repo.get_active_alerts(limit=limit)

    def get_active_cards(self, limit: int = 10, today: date | None = None) -> list[AnomalyCard]:
        """Return active alerts projected onto the design-facing card shape (#508)."""
        alerts = self._repo.get_active_alerts(limit=limit)
        return [to_anomaly_card(a, today=today) for a in alerts]

    def get_history(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
    ) -> list[AnomalyAlertResponse]:
        """Return alert history within date range."""
        return self._repo.get_alert_history(start_date, end_date, limit)

    def acknowledge(self, alert_id: int, user: str) -> bool:
        """Acknowledge an alert."""
        return self._repo.acknowledge_alert(alert_id, user)
