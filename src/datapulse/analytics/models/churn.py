"""Churn, returns, affinity, and ABC analysis models.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


class ReturnAnalysis(BaseModel):
    """Return/credit note analysis per product-customer pair."""

    model_config = ConfigDict(frozen=True)

    drug_name: str
    drug_brand: str = ""
    customer_name: str
    origin: str = ""
    return_quantity: JsonDecimal
    return_amount: JsonDecimal
    return_count: int


class ReturnsTrendPoint(BaseModel):
    """Returns trend data point."""

    model_config = ConfigDict(frozen=True)

    period: str
    return_count: int
    return_amount: JsonDecimal
    return_rate: JsonDecimal


class ReturnsTrend(BaseModel):
    """Returns trend over time."""

    model_config = ConfigDict(frozen=True)

    points: list[ReturnsTrendPoint]
    total_returns: int
    total_return_amount: JsonDecimal
    avg_return_rate: JsonDecimal


class ABCItem(BaseModel):
    """Product classified by ABC analysis (revenue contribution)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    key: int
    name: str
    value: JsonDecimal
    cumulative_pct: JsonDecimal
    abc_class: str  # "A", "B", "C"


class ABCAnalysis(BaseModel):
    """ABC/Pareto analysis result."""

    model_config = ConfigDict(frozen=True)

    items: list[ABCItem]
    total: JsonDecimal
    class_a_count: int
    class_b_count: int
    class_c_count: int
    class_a_pct: JsonDecimal
    class_b_pct: JsonDecimal
    class_c_pct: JsonDecimal


class ChurnPrediction(BaseModel):
    """Customer churn prediction result."""

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_name: str
    health_score: JsonDecimal
    health_band: str
    recency_days: int
    frequency_3m: int
    monetary_3m: JsonDecimal
    trend: str
    rfm_segment: str
    churn_probability: JsonDecimal
    risk_level: str


class AffinityPair(BaseModel):
    """A pair of frequently co-purchased products."""

    model_config = ConfigDict(frozen=True)

    related_key: int
    related_name: str
    co_occurrence_count: int
    support_pct: JsonDecimal
    confidence: JsonDecimal
