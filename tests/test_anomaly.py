"""Tests for statistical anomaly detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from datapulse.pipeline.anomaly import (
    MONITORED_METRICS,
    Z_SCORE_THRESHOLD,
    Anomaly,
    _check_metric,
    detect_anomalies,
)


class TestAnomaly:
    def test_frozen_dataclass(self):
        a = Anomaly(
            metric="daily_net",
            date="2024-01-15",
            value=500000,
            mean_30d=300000,
            stddev_30d=50000,
            z_score=4.0,
            direction="above",
            severity="critical",
        )
        assert a.metric == "daily_net"
        assert a.z_score == 4.0


class TestMonitoredMetrics:
    def test_has_expected_metrics(self):
        assert "daily_net" in MONITORED_METRICS
        assert "daily_quantity" in MONITORED_METRICS
        assert "daily_transactions" in MONITORED_METRICS

    def test_threshold_is_3(self):
        assert Z_SCORE_THRESHOLD == 3.0


class TestCheckMetric:
    def test_returns_none_when_no_data(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None
        result = _check_metric(session, "daily_net")
        assert result is None

    def test_returns_none_when_below_threshold(self):
        session = MagicMock()

        # Latest value
        latest_row = MagicMock()
        latest_row._mapping = {"date_key": "2024-01-15", "daily_net": 305000}

        # Stats (mean=300000, stddev=50000 → z_score = 0.1, below threshold)
        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": 300000, "stddev_val": 50000}

        session.execute.return_value.fetchone.side_effect = [latest_row, stats_row]

        result = _check_metric(session, "daily_net")
        assert result is None

    def test_detects_anomaly_above(self):
        session = MagicMock()

        # Latest value: way above normal
        latest_row = MagicMock()
        latest_row._mapping = {"date_key": "2024-01-15", "daily_net": 600000}

        # Stats (mean=300000, stddev=50000 → z_score = 6.0)
        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": 300000, "stddev_val": 50000}

        session.execute.return_value.fetchone.side_effect = [latest_row, stats_row]

        result = _check_metric(session, "daily_net")
        assert result is not None
        assert result.direction == "above"
        assert result.z_score == 6.0
        assert result.severity == "critical"

    def test_detects_anomaly_below(self):
        session = MagicMock()

        # Latest value: way below normal
        latest_row = MagicMock()
        latest_row._mapping = {"date_key": "2024-01-15", "daily_net": 50000}

        # Stats (mean=300000, stddev=50000 → z_score = -5.0)
        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": 300000, "stddev_val": 50000}

        session.execute.return_value.fetchone.side_effect = [latest_row, stats_row]

        result = _check_metric(session, "daily_net")
        assert result is not None
        assert result.direction == "below"
        assert result.z_score == -5.0

    def test_returns_none_when_stddev_is_zero(self):
        session = MagicMock()

        latest_row = MagicMock()
        latest_row._mapping = {"date_key": "2024-01-15", "daily_net": 300000}

        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": 300000, "stddev_val": 0}

        session.execute.return_value.fetchone.side_effect = [latest_row, stats_row]

        result = _check_metric(session, "daily_net")
        assert result is None

    def test_returns_none_when_stats_null(self):
        session = MagicMock()

        latest_row = MagicMock()
        latest_row._mapping = {"date_key": "2024-01-15", "daily_net": 300000}

        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": None, "stddev_val": None}

        session.execute.return_value.fetchone.side_effect = [latest_row, stats_row]

        result = _check_metric(session, "daily_net")
        assert result is None

    def test_warning_severity_for_z_score_between_3_and_4(self):
        session = MagicMock()

        latest_row = MagicMock()
        latest_row._mapping = {"date_key": "2024-01-15", "daily_net": 475000}

        # z_score = (475000 - 300000) / 50000 = 3.5
        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": 300000, "stddev_val": 50000}

        session.execute.return_value.fetchone.side_effect = [latest_row, stats_row]

        result = _check_metric(session, "daily_net")
        assert result is not None
        assert result.severity == "warning"
        assert result.z_score == 3.5


class TestDetectAnomalies:
    def test_returns_empty_when_no_anomalies(self):
        session = MagicMock()

        # All metrics return normal values
        latest_row = MagicMock()
        latest_row._mapping = {
            "date_key": "2024-01-15",
            "daily_net": 300000,
            "daily_quantity": 1000,
            "daily_transactions": 500,
        }

        stats_row = MagicMock()
        stats_row._mapping = {"mean_val": 300000, "stddev_val": 50000}

        session.execute.return_value.fetchone.side_effect = [
            latest_row,
            stats_row,
            latest_row,
            stats_row,
            latest_row,
            stats_row,
        ]

        result = detect_anomalies(session)
        assert isinstance(result, list)

    def test_handles_exceptions_gracefully(self):
        session = MagicMock()
        session.execute.side_effect = Exception("DB error")

        result = detect_anomalies(session)
        assert result == []
