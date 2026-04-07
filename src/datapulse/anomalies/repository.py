"""Anomaly alert persistence — CRUD for anomaly_alerts table."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.anomalies.models import AnomalyAlertResponse, DetectedAnomaly
from datapulse.logging import get_logger

log = get_logger(__name__)


class AnomalyRepository:
    """CRUD operations for the anomaly_alerts table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_alerts(self, alerts: list[DetectedAnomaly], tenant_id: int = 1) -> int:
        """Insert detected anomalies into the anomaly_alerts table."""
        if not alerts:
            return 0

        rows_written = 0
        for alert in alerts:
            stmt = text("""
                INSERT INTO public.anomaly_alerts
                    (tenant_id, metric, period, actual_value, expected_value,
                     lower_bound, upper_bound, z_score, severity, direction,
                     is_suppressed, suppression_reason)
                VALUES
                    (:tid, :metric, :period, :actual, :expected,
                     :lower, :upper, :z, :severity, :direction,
                     :suppressed, :reason)
            """)
            self._session.execute(
                stmt,
                {
                    "tid": tenant_id,
                    "metric": alert.metric,
                    "period": alert.period,
                    "actual": float(alert.actual_value),
                    "expected": float(alert.expected_value),
                    "lower": float(alert.lower_bound),
                    "upper": float(alert.upper_bound),
                    "z": float(alert.z_score) if alert.z_score is not None else None,
                    "severity": alert.severity,
                    "direction": alert.direction,
                    "suppressed": alert.is_suppressed,
                    "reason": alert.suppression_reason,
                },
            )
            rows_written += 1

        self._session.flush()
        log.info("anomaly_alerts_saved", count=rows_written)
        return rows_written

    def get_active_alerts(self, limit: int = 20) -> list[AnomalyAlertResponse]:
        """Return unacknowledged, unsuppressed alerts (most recent first)."""
        stmt = text("""
            SELECT id, metric, period, actual_value, expected_value,
                   z_score, severity, direction, is_suppressed,
                   suppression_reason, acknowledged
            FROM public.anomaly_alerts
            WHERE acknowledged = FALSE AND is_suppressed = FALSE
            ORDER BY detected_at DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"limit": limit}).fetchall()
        return [self._to_response(r) for r in rows]

    def get_alert_history(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
    ) -> list[AnomalyAlertResponse]:
        """Return all alerts within a date range."""
        clauses = []
        params: dict = {"limit": limit}

        if start_date is not None:
            clauses.append("period >= :start")
            params["start"] = start_date
        if end_date is not None:
            clauses.append("period <= :end")
            params["end"] = end_date

        where = " AND ".join(clauses) if clauses else "1=1"
        stmt = text(f"""
            SELECT id, metric, period, actual_value, expected_value,
                   z_score, severity, direction, is_suppressed,
                   suppression_reason, acknowledged
            FROM public.anomaly_alerts
            WHERE {where}
            ORDER BY detected_at DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return [self._to_response(r) for r in rows]

    def acknowledge_alert(self, alert_id: int, user: str) -> bool:
        """Mark an alert as acknowledged."""
        stmt = text("""
            UPDATE public.anomaly_alerts
            SET acknowledged = TRUE,
                acknowledged_at = now(),
                acknowledged_by = :user,
                updated_at = now()
            WHERE id = :id AND acknowledged = FALSE
        """)
        result = self._session.execute(stmt, {"id": alert_id, "user": user})
        self._session.flush()
        return result.rowcount > 0  # type: ignore[attr-defined]

    @staticmethod
    def _to_response(row) -> AnomalyAlertResponse:
        return AnomalyAlertResponse(
            id=int(row[0]),
            metric=str(row[1]),
            period=row[2],
            actual_value=Decimal(str(row[3])),
            expected_value=Decimal(str(row[4])),
            z_score=Decimal(str(row[5])) if row[5] is not None else None,
            severity=str(row[6]),
            direction=str(row[7]),
            is_suppressed=bool(row[8]),
            suppression_reason=str(row[9]) if row[9] else None,
            acknowledged=bool(row[10]),
        )
