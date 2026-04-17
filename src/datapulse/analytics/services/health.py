"""HealthService — customer health scores and distributions."""

from __future__ import annotations

from datapulse.analytics.customer_health import CustomerHealthRepository
from datapulse.analytics.models import (
    CustomerHealthScore,
    HealthDistribution,
)
from datapulse.cache_decorator import cached
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:analytics"


class HealthService:
    """Customer health scoring and distribution analytics."""

    def __init__(self, customer_health_repo: CustomerHealthRepository | None = None) -> None:
        self._customer_health_repo = customer_health_repo

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_health(
        self,
        band: str | None = None,
        limit: int = 50,
    ) -> list[CustomerHealthScore]:
        """Customer health scores, optionally filtered by band (cached 300s)."""
        if self._customer_health_repo is None:
            raise RuntimeError("CustomerHealthRepository not configured")
        return self._customer_health_repo.get_health_scores(band=band, limit=limit)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_health_distribution(self) -> HealthDistribution:
        """Distribution of customers across health bands (cached 300s)."""
        if self._customer_health_repo is None:
            raise RuntimeError("CustomerHealthRepository not configured")
        return self._customer_health_repo.get_health_distribution()

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_at_risk_customers(self, limit: int = 20) -> list[CustomerHealthScore]:
        """At-risk and critical customers, lowest score first (cached 300s)."""
        if self._customer_health_repo is None:
            raise RuntimeError("CustomerHealthRepository not configured")
        return self._customer_health_repo.get_at_risk_customers(limit=limit)
