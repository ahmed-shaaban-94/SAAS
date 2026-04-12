"""Repository for fetching baseline data for scenario simulations."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class ScenarioRepository:
    """Fetches monthly baseline aggregates from the marts schema."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_monthly_baseline(self, months: int) -> list[dict]:
        """Return last N months of revenue, cost, and volume from metrics_summary.

        Falls back to fct_sales aggregation if metrics_summary lacks monthly data.
        """
        sql = text("""
            SELECT
                TO_CHAR(d.month_start_date, 'YYYY-MM') AS month,
                COALESCE(SUM(f.total_amount), 0) AS revenue,
                COALESCE(SUM(f.cost_amount), 0) AS cost,
                COALESCE(SUM(f.quantity), 0) AS volume
            FROM public_marts.fct_sales f
            JOIN public_marts.dim_date d ON f.date_key = d.date_key
            WHERE d.month_start_date >= (
                SELECT MAX(month_start_date) - (INTERVAL '1 month' * :months)
                FROM public_marts.dim_date
            )
            GROUP BY d.month_start_date, TO_CHAR(d.month_start_date, 'YYYY-MM')
            ORDER BY d.month_start_date
            LIMIT :limit
        """)
        rows = self._session.execute(sql, {"months": months, "limit": months}).fetchall()
        return [
            {
                "month": row[0],
                "revenue": Decimal(str(row[1])),
                "cost": Decimal(str(row[2])),
                "volume": int(row[3]),
            }
            for row in rows
        ]

    def get_average_price(self) -> Decimal:
        """Return average unit price across recent sales."""
        sql = text("""
            SELECT COALESCE(AVG(unit_price), 0)
            FROM public_marts.fct_sales
            WHERE date_key >= (SELECT MAX(date_key) - 365 FROM public_marts.fct_sales)
        """)
        result = self._session.execute(sql).scalar()
        return Decimal(str(result or 0))
