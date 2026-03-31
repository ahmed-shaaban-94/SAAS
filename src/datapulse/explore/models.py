"""Pydantic models for the Explore engine.

Defines the schema for dimensions, metrics, joins, explore queries,
and explore results — the contract between the dbt YAML parser,
the SQL builder, and the API layer.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# ------------------------------------------------------------------
# Catalog models (parsed from dbt YAML)
# ------------------------------------------------------------------


class DimensionType(StrEnum):
    """Column type hint for frontend field rendering."""

    string = "string"
    number = "number"
    date = "date"
    boolean = "boolean"


class MetricType(StrEnum):
    """Supported aggregation functions."""

    sum = "sum"
    average = "average"
    count = "count"
    count_distinct = "count_distinct"
    min = "min"
    max = "max"


class Dimension(BaseModel):
    """A queryable dimension column from a dbt model."""

    name: str = Field(..., description="Column name in the database")
    label: str = Field(..., description="Human-readable display name")
    description: str = ""
    dimension_type: DimensionType = DimensionType.string
    model: str = Field(..., description="Source dbt model name")


class Metric(BaseModel):
    """An aggregation metric defined on a dbt model column."""

    name: str = Field(..., description="Metric identifier (e.g. total_sales)")
    label: str = Field(..., description="Human-readable display name")
    description: str = ""
    metric_type: MetricType = Field(..., description="Aggregation function")
    column: str = Field(..., description="Source column to aggregate")
    model: str = Field(..., description="Source dbt model name")


class JoinPath(BaseModel):
    """A JOIN relationship between two dbt models."""

    join_model: str = Field(..., description="Target model to join")
    sql_on: str = Field(..., description="JOIN ON clause (uses ${model.column} syntax)")


class ExploreModel(BaseModel):
    """A single dbt model exposed for exploration."""

    name: str = Field(..., description="dbt model name (= DB table name)")
    label: str = ""
    description: str = ""
    schema_name: str = Field("public_marts", description="Database schema")
    dimensions: list[Dimension] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    joins: list[JoinPath] = Field(default_factory=list)


class ExploreCatalog(BaseModel):
    """The full catalog of all explorable models."""

    models: list[ExploreModel] = Field(default_factory=list)


# ------------------------------------------------------------------
# Query models (from API request)
# ------------------------------------------------------------------


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class SortSpec(BaseModel):
    """Sort specification for explore query results."""

    field: str = Field(..., description="Dimension or metric name to sort by")
    direction: SortDirection = SortDirection.desc


class ExploreFilter(BaseModel):
    """A single filter condition for an explore query."""

    field: str = Field(..., description="Dimension name to filter on")
    operator: str = Field(
        "eq",
        description="Comparison operator: eq, neq, gt, gte, lt, lte, in, like",
    )
    value: str | int | float | bool | list[str] = Field(..., description="Filter value(s)")


class ExploreQuery(BaseModel):
    """An explore query request — dimensions + metrics + filters."""

    model: str = Field(..., description="Base model to query")
    dimensions: list[str] = Field(
        default_factory=list, description="Dimension column names to GROUP BY"
    )
    metrics: list[str] = Field(default_factory=list, description="Metric names to aggregate")
    filters: list[ExploreFilter] = Field(default_factory=list, description="WHERE conditions")
    sorts: list[SortSpec] = Field(default_factory=list, description="ORDER BY specs")
    limit: int = Field(500, ge=1, le=10_000, description="Max rows to return")


# ------------------------------------------------------------------
# Result models (API response)
# ------------------------------------------------------------------


class ExploreResult(BaseModel):
    """Result of an explore query execution."""

    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    row_count: int = 0
    sql: str = Field("", description="Generated SQL for transparency")
    truncated: bool = False
