"""Analytics sub-services — domain-scoped service classes.

Each sub-service owns one slice of the analytics domain:
- KPIService       : KPI summary, dashboard, date range, filter options
- RankingService   : trends, rankings, comparisons, advanced analytics
- BreakdownService : billing / customer-type breakdowns
- DetailService    : per-entity detail + feature store + lifecycle
- HealthService    : customer health scores
- ChurnService     : churn predictions + product affinity
"""

from datapulse.analytics.services.breakdown import BreakdownService
from datapulse.analytics.services.churn import ChurnService
from datapulse.analytics.services.detail import DetailService
from datapulse.analytics.services.health import HealthService
from datapulse.analytics.services.kpi import KPIService
from datapulse.analytics.services.ranking import RankingService

__all__ = [
    "BreakdownService",
    "ChurnService",
    "DetailService",
    "HealthService",
    "KPIService",
    "RankingService",
]
