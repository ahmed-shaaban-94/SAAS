"""Customer health scoring models.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


class CustomerHealthScore(BaseModel):
    """Composite health score for a single customer."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_name: str
    health_score: JsonDecimal
    health_band: str  # "Thriving" | "Healthy" | "Needs Attention" | "At Risk" | "Critical"
    recency_days: int
    frequency_3m: int
    monetary_3m: JsonDecimal
    return_rate: JsonDecimal
    product_diversity: int
    trend: str  # "improving" | "stable" | "declining"


class HealthDistribution(BaseModel):
    """Distribution of customers across health bands."""

    model_config = ConfigDict(frozen=True)

    thriving: int = 0
    healthy: int = 0
    needs_attention: int = 0
    at_risk: int = 0
    critical: int = 0
    total: int = 0
