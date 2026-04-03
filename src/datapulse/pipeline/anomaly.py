"""Statistical anomaly detection for pipeline metrics.

Uses z-score method (3-sigma rule) to detect anomalies in daily
metrics by comparing the latest value against a rolling 30-day window.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)

# Metrics to check for anomalies (column names in metrics_summary)
MONITORED_METRICS = (
    "daily_net",
    "daily_quantity",
    "daily_transactions",
)

# Z-score threshold for anomaly detection (3-sigma = 99.7% confidence)
Z_SCORE_THRESHOLD = 3.0


@dataclass(frozen=True)
class Anomaly:
    """A detected statistical anomaly in a metric."""

    metric: str
    date: str
    value: float
    mean_30d: float
    stddev_30d: float
    z_score: float
    direction: str  # "above" or "below"
    severity: str  # "warning" (|z| 3-4) or "critical" (|z| > 4)


def detect_anomalies(session: Session) -> list[Anomaly]:
    """Detect statistical anomalies in the latest daily metrics.

    For each monitored metric in metrics_summary:
    1. Calculate rolling 30-day mean and stddev (excluding latest day)
    2. Compute z-score for the latest value
    3. Flag if |z-score| > Z_SCORE_THRESHOLD

    Returns a list of detected anomalies, empty if none found.
    """
    anomalies: list[Anomaly] = []

    for metric in MONITORED_METRICS:
        try:
            anomaly = _check_metric(session, metric)
            if anomaly is not None:
                anomalies.append(anomaly)
        except Exception as exc:
            log.warning("anomaly_check_failed", metric=metric, error=str(exc))

    if anomalies:
        log.info("anomalies_detected", count=len(anomalies))
    return anomalies


def _check_metric(session: Session, metric: str) -> Anomaly | None:
    """Check a single metric for anomalies using z-score."""
    # Get the latest date and value
    latest_stmt = text(f"""
        SELECT date_key::text AS date_key, {metric}
        FROM public_marts.metrics_summary
        WHERE {metric} IS NOT NULL
        ORDER BY date_key DESC
        LIMIT 1
    """)
    latest_row = session.execute(latest_stmt).fetchone()
    if latest_row is None:
        return None

    latest_date = latest_row._mapping["date_key"]
    latest_value = float(latest_row._mapping[metric])

    # Calculate 30-day rolling stats (excluding the latest day)
    stats_stmt = text(f"""
        SELECT AVG({metric}) AS mean_val, STDDEV({metric}) AS stddev_val
        FROM public_marts.metrics_summary
        WHERE date_key < :latest_date::date
          AND date_key >= :latest_date::date - INTERVAL '30 days'
          AND {metric} IS NOT NULL
    """)
    stats_row = session.execute(stats_stmt, {"latest_date": latest_date}).fetchone()
    if stats_row is None:
        return None

    mean_val = stats_row._mapping["mean_val"]
    stddev_val = stats_row._mapping["stddev_val"]

    if mean_val is None or stddev_val is None or float(stddev_val) == 0:
        return None

    mean_30d = float(mean_val)
    stddev_30d = float(stddev_val)

    z_score = (latest_value - mean_30d) / stddev_30d

    if abs(z_score) < Z_SCORE_THRESHOLD:
        return None

    direction = "above" if z_score > 0 else "below"
    severity = "critical" if abs(z_score) > 4.0 else "warning"

    return Anomaly(
        metric=metric,
        date=latest_date,
        value=round(latest_value, 2),
        mean_30d=round(mean_30d, 2),
        stddev_30d=round(stddev_30d, 2),
        z_score=round(z_score, 2),
        direction=direction,
        severity=severity,
    )
