"""Shared base types used by multiple analytics domains.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class DataDateRange(BaseModel):
    """Min/max dates of available data."""

    model_config = ConfigDict(frozen=True)

    min_date: date
    max_date: date


class DateRange(BaseModel):
    """Inclusive date range for filtering queries."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date


class AnalyticsFilter(BaseModel):
    """Common filter parameters accepted by all analytics queries."""

    model_config = ConfigDict(frozen=True)

    date_range: DateRange | None = None
    site_key: int | None = None
    category: str | None = None
    brand: str | None = None
    staff_key: int | None = None
    limit: int = Field(default=10, ge=1, le=100)


class TimeSeriesPoint(BaseModel):
    """Single data point in a time series (daily or monthly)."""

    model_config = ConfigDict(frozen=True)

    period: str  # "2024-01" or "2024-01-15"
    value: JsonDecimal


class StatisticalAnnotation(BaseModel):
    """Statistical confidence metadata for a metric or trend."""

    model_config = ConfigDict(frozen=True)

    z_score: JsonDecimal | None = None
    cv: JsonDecimal | None = None
    significance: str | None = None  # "significant" | "inconclusive" | "noise"


class FilterOption(BaseModel):
    """Single key-label pair for dropdown/slicer population."""

    model_config = ConfigDict(frozen=True)

    key: int
    label: str


class FilterOptions(BaseModel):
    """Available filter values for all analytics slicers."""

    model_config = ConfigDict(frozen=True)

    categories: list[str]
    brands: list[str]
    sites: list[FilterOption]
    staff: list[FilterOption]
