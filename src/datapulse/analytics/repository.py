"""Read-only analytics repository — composed from focused sub-repositories.

Public interface is unchanged: callers still use ``AnalyticsRepository`` as a
single class. The implementation is split across four mixin classes for
maintainability:

- ``KpiRepository``      — KPI summaries, filter options, sparklines
- ``TrendRepository``    — Daily / monthly time-series trends
- ``RankingRepository``  — Top-N product / customer / staff / site rankings
- ``ReturnsRepository``  — Return analysis and staff quota
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from datapulse.analytics.kpi_repository import KpiRepository
from datapulse.analytics.ranking_repository import RankingRepository
from datapulse.analytics.returns_repository import ReturnsRepository
from datapulse.analytics.trend_repository import TrendRepository


class AnalyticsRepository(KpiRepository, TrendRepository, RankingRepository, ReturnsRepository):
    """Aggregates all analytics query capabilities.

    Inherits from four focused mixin repositories.  The MRO ensures all
    public methods are accessible on a single ``AnalyticsRepository`` instance.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
