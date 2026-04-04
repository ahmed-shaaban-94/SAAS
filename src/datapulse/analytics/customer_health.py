"""Customer health score repository — queries the feat_customer_health dbt model."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    CustomerHealthScore,
    HealthDistribution,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class CustomerHealthRepository:
    """Read-only queries against the customer health feature table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_health_scores(
        self,
        *,
        band: str | None = None,
        limit: int = 50,
    ) -> list[CustomerHealthScore]:
        """Return customer health scores, optionally filtered by band."""
        log.info("get_health_scores", band=band, limit=limit)

        where = "1=1"
        params: dict = {"limit": limit}
        if band is not None:
            where = "health_band = :band"
            params["band"] = band

        stmt = text(f"""
            SELECT customer_key, customer_name, health_score, health_band,
                   recency_days, frequency_3m, monetary_3m, return_rate,
                   product_diversity, trend
            FROM public_marts.feat_customer_health
            WHERE {where}
            ORDER BY health_score DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()

        return [
            CustomerHealthScore(
                customer_key=int(r[0]),
                customer_name=str(r[1]),
                health_score=Decimal(str(r[2])),
                health_band=str(r[3]),
                recency_days=int(r[4]),
                frequency_3m=int(r[5]),
                monetary_3m=Decimal(str(r[6])),
                return_rate=Decimal(str(r[7])),
                product_diversity=int(r[8]),
                trend=str(r[9]),
            )
            for r in rows
        ]

    def get_health_distribution(self) -> HealthDistribution:
        """Return count of customers in each health band."""
        log.info("get_health_distribution")

        stmt = text("""
            SELECT health_band, COUNT(*) AS cnt
            FROM public_marts.feat_customer_health
            GROUP BY health_band
        """)
        rows = self._session.execute(stmt).fetchall()

        band_counts: dict[str, int] = {}
        total = 0
        for r in rows:
            band_counts[str(r[0])] = int(r[1])
            total += int(r[1])

        return HealthDistribution(
            thriving=band_counts.get("Thriving", 0),
            healthy=band_counts.get("Healthy", 0),
            needs_attention=band_counts.get("Needs Attention", 0),
            at_risk=band_counts.get("At Risk", 0),
            critical=band_counts.get("Critical", 0),
            total=total,
        )

    def get_at_risk_customers(self, limit: int = 20) -> list[CustomerHealthScore]:
        """Return customers in At Risk or Critical bands, lowest score first."""
        log.info("get_at_risk_customers", limit=limit)

        stmt = text("""
            SELECT customer_key, customer_name, health_score, health_band,
                   recency_days, frequency_3m, monetary_3m, return_rate,
                   product_diversity, trend
            FROM public_marts.feat_customer_health
            WHERE health_band IN ('At Risk', 'Critical')
            ORDER BY health_score ASC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"limit": limit}).fetchall()

        return [
            CustomerHealthScore(
                customer_key=int(r[0]),
                customer_name=str(r[1]),
                health_score=Decimal(str(r[2])),
                health_band=str(r[3]),
                recency_days=int(r[4]),
                frequency_3m=int(r[5]),
                monetary_3m=Decimal(str(r[6])),
                return_rate=Decimal(str(r[7])),
                product_diversity=int(r[8]),
                trend=str(r[9]),
            )
            for r in rows
        ]
