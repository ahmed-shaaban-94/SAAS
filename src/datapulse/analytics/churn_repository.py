"""Repository for customer churn prediction queries."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class ChurnRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_churn_predictions(
        self,
        risk_level: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch churn predictions, optionally filtered by risk level."""
        conditions = []
        params: dict = {"limit": limit}

        if risk_level:
            conditions.append("risk_level = :risk_level")
            params["risk_level"] = risk_level

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        stmt = text(f"""
            SELECT customer_key, customer_name, health_score, health_band,
                   recency_days, frequency_3m, monetary_3m, trend,
                   rfm_segment, churn_probability, risk_level
            FROM public_marts.feat_churn_prediction
            {where}
            ORDER BY churn_probability DESC
            LIMIT :limit
        """)  # noqa: S608
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    def get_risk_distribution(self) -> list[dict]:
        """Count customers per risk level."""
        stmt = text("""
            SELECT risk_level, COUNT(*) AS count
            FROM public_marts.feat_churn_prediction
            GROUP BY risk_level
            ORDER BY CASE risk_level WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
        """)
        rows = self._session.execute(stmt).mappings().all()
        return [dict(r) for r in rows]
