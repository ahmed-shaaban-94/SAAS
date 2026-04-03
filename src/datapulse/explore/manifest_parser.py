"""dbt YAML manifest parser.

Reads dbt model YAML files (``_*__models.yml``) to auto-discover
dimensions, metrics, and joins.  Builds an in-memory ``ExploreCatalog``
that the SQL builder and API layer consume.

The parser reads:
- ``meta.joins`` on models (join paths to dimensions)
- ``meta.metrics`` on columns (aggregation definitions)
- ``meta.label`` on models (human-readable name)
- Column ``name`` and ``description`` for dimensions
"""

from __future__ import annotations

import re
import threading
import time as _time
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from datapulse.explore.models import (
    Dimension,
    DimensionType,
    ExploreCatalog,
    ExploreModel,
    JoinPath,
    Metric,
    MetricType,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

# Columns that are internal / not useful as explore dimensions
_SKIP_COLUMNS = {"tenant_id", "sales_key"}

# Heuristic: column names containing these patterns are numeric
_NUMERIC_PATTERNS = re.compile(
    r"(quantity|sales|discount|amount|count|rate|growth|size|ratio|value|pct)",
    re.IGNORECASE,
)

# Heuristic: column names containing these patterns are dates
_DATE_PATTERNS = re.compile(r"(date|_at$|year_month|year_week)", re.IGNORECASE)

# Heuristic: boolean columns
_BOOL_PATTERNS = re.compile(r"^(is_|has_)", re.IGNORECASE)


def _infer_dimension_type(col_name: str) -> DimensionType:
    """Infer column type from naming conventions."""
    if _BOOL_PATTERNS.search(col_name):
        return DimensionType.boolean
    if _DATE_PATTERNS.search(col_name):
        return DimensionType.date
    if _NUMERIC_PATTERNS.search(col_name):
        return DimensionType.number
    if col_name.endswith("_key"):
        return DimensionType.number
    return DimensionType.string


def _col_to_label(col_name: str) -> str:
    """Convert snake_case column name to Title Case label."""
    return col_name.replace("_", " ").title()


def _parse_model_yaml(model_dict: dict, schema: str = "public_marts") -> ExploreModel:
    """Parse a single dbt model definition from YAML into an ExploreModel."""
    name = model_dict["name"]
    description = model_dict.get("description", "")
    meta = model_dict.get("meta", {})
    label = meta.get("label", _col_to_label(name))

    # Parse joins
    joins: list[JoinPath] = []
    for j in meta.get("joins", []):
        joins.append(
            JoinPath(
                join_model=j["join"],
                sql_on=j["sql_on"],
            )
        )

    # Parse columns -> dimensions + metrics
    dimensions: list[Dimension] = []
    metrics: list[Metric] = []

    for col in model_dict.get("columns", []):
        col_name = col["name"]
        col_desc = col.get("description", "")
        col_meta = col.get("meta", {})

        # Skip internal columns
        if col_name in _SKIP_COLUMNS:
            continue

        # Extract metrics from meta.metrics
        col_metrics = col_meta.get("metrics", {})
        for metric_name, metric_def in col_metrics.items():
            raw_type = metric_def.get("type", "sum")
            try:
                mtype = MetricType(raw_type)
            except ValueError:
                mtype = MetricType.sum

            metrics.append(
                Metric(
                    name=metric_name,
                    label=_col_to_label(metric_name),
                    description=col_desc,
                    metric_type=mtype,
                    column=col_name,
                    model=name,
                )
            )

        # All columns become dimensions (even metric source columns,
        # since users may want to filter/group by them)
        dim_type = (
            DimensionType(col_meta.get("dimension_type", ""))
            if col_meta.get("dimension_type")
            else _infer_dimension_type(col_name)
        )

        dimensions.append(
            Dimension(
                name=col_name,
                label=col_meta.get("label", _col_to_label(col_name)),
                description=col_desc,
                dimension_type=dim_type,
                model=name,
            )
        )

    return ExploreModel(
        name=name,
        label=label,
        description=description,
        schema_name=schema,
        dimensions=dimensions,
        metrics=metrics,
        joins=joins,
    )


def parse_dbt_yaml(yaml_path: Path) -> list[ExploreModel]:
    """Parse a single dbt YAML file and return a list of ExploreModels."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if not data or "models" not in data:
        return []

    models: list[ExploreModel] = []
    for model_dict in data["models"]:
        try:
            models.append(_parse_model_yaml(model_dict))
        except Exception as exc:
            log.warning(
                "yaml_parse_error",
                file=str(yaml_path),
                model=model_dict.get("name", "unknown"),
                error=str(exc),
            )

    return models


def build_catalog(dbt_models_dir: str | Path) -> ExploreCatalog:
    """Scan the dbt models directory for all YAML files and build a catalog.

    Looks for files matching ``_*__models.yml`` and ``_*__sources.yml``
    in the marts directory tree.
    """
    models_dir = Path(dbt_models_dir)
    all_models: list[ExploreModel] = []

    # Scan marts directory (facts, dims, aggs)
    marts_dir = models_dir / "marts"
    if not marts_dir.exists():
        log.warning("marts_dir_not_found", path=str(marts_dir))
        return ExploreCatalog(models=[])

    for yaml_file in sorted(marts_dir.rglob("_*__models.yml")):
        log.info("parsing_dbt_yaml", file=str(yaml_file))
        parsed = parse_dbt_yaml(yaml_file)
        all_models.extend(parsed)

    log.info(
        "catalog_built",
        model_count=len(all_models),
        total_dimensions=sum(len(m.dimensions) for m in all_models),
        total_metrics=sum(len(m.metrics) for m in all_models),
    )

    return ExploreCatalog(models=all_models)


# ---------------------------------------------------------------------------
# Thread-safe cached catalog singleton
# ---------------------------------------------------------------------------
_catalog_lock = threading.Lock()
_cached_catalog: ExploreCatalog | None = None
_catalog_built_at: float = 0.0
_CATALOG_TTL: float = 300.0  # 5 minutes


def get_catalog(models_dir: str | Path) -> ExploreCatalog:
    """Return a cached catalog, rebuilding if TTL expired (thread-safe)."""
    global _cached_catalog, _catalog_built_at  # noqa: PLW0603
    now = _time.monotonic()
    if _cached_catalog is not None and (now - _catalog_built_at) < _CATALOG_TTL:
        return _cached_catalog
    with _catalog_lock:
        # Double-check after acquiring lock (another thread may have rebuilt)
        if _cached_catalog is not None and (_time.monotonic() - _catalog_built_at) < _CATALOG_TTL:
            return _cached_catalog
        _cached_catalog = build_catalog(models_dir)
        _catalog_built_at = _time.monotonic()
        return _cached_catalog


def invalidate_catalog() -> None:
    """Force the next ``get_catalog`` call to rebuild."""
    global _cached_catalog, _catalog_built_at  # noqa: PLW0603
    with _catalog_lock:
        _cached_catalog = None
        _catalog_built_at = 0.0
