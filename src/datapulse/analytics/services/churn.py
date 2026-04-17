"""ChurnService — churn predictions and product affinity."""

from __future__ import annotations

from datapulse.analytics.affinity_repository import AffinityRepository
from datapulse.analytics.churn_repository import ChurnRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


class ChurnService:
    """Customer churn predictions and product co-purchase affinity."""

    def __init__(
        self,
        churn_repo: ChurnRepository | None = None,
        affinity_repo: AffinityRepository | None = None,
    ) -> None:
        self._churn_repo = churn_repo
        self._affinity_repo = affinity_repo

    def get_churn_predictions(
        self,
        risk_level: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Customer churn predictions sorted by probability."""
        if self._churn_repo is None:
            raise RuntimeError("ChurnRepository not configured")
        return self._churn_repo.get_churn_predictions(risk_level=risk_level, limit=limit)

    def get_affinity_for_product(
        self,
        product_key: int,
        limit: int = 10,
    ) -> list[dict]:
        """Top co-purchased products for a given product."""
        if self._affinity_repo is None:
            raise RuntimeError("AffinityRepository not configured")
        return self._affinity_repo.get_affinity_for_product(product_key=product_key, limit=limit)
