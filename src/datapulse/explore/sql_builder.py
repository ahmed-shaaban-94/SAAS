"""Dynamic SQL generator for explore queries.

Takes an ``ExploreQuery`` and an ``ExploreCatalog``, validates all
requested fields against the catalog (whitelist-based), and generates
parameterised SQL.  This prevents SQL injection by construction —
only columns and tables present in the parsed catalog are allowed.
"""

from __future__ import annotations

import re

from datapulse.explore.models import (
    ExploreCatalog,
    ExploreModel,
    ExploreQuery,
    Metric,
    MetricType,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

# Aggregation SQL templates per metric type
_AGG_SQL = {
    MetricType.sum: "SUM({col})",
    MetricType.average: "AVG({col})",
    MetricType.count: "COUNT({col})",
    MetricType.count_distinct: "COUNT(DISTINCT {col})",
    MetricType.min: "MIN({col})",
    MetricType.max: "MAX({col})",
}

# Filter operator SQL templates
_FILTER_OPS = {
    "eq": "{col} = :{param}",
    "neq": "{col} != :{param}",
    "gt": "{col} > :{param}",
    "gte": "{col} >= :{param}",
    "lt": "{col} < :{param}",
    "lte": "{col} <= :{param}",
    "like": "{col} ILIKE :{param}",
}

# Regex to parse ${model.column} syntax in join sql_on
_JOIN_REF = re.compile(r"\$\{(\w+)\.(\w+)\}")

# Only allow safe SQL identifiers (lowercase letters, digits, underscores)
_SAFE_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _resolve_join_on(sql_on: str, base_alias: str, join_alias: str) -> str:
    """Resolve ``${model.column}`` references in a JOIN ON clause to table aliases."""

    def replacer(match):
        model = match.group(1)
        column = match.group(2)
        # Map model name to alias — we use the model name as alias
        return f"{model}.{column}"

    return _JOIN_REF.sub(replacer, sql_on)


def _find_model(catalog: ExploreCatalog, model_name: str) -> ExploreModel | None:
    """Find a model in the catalog by name."""
    for m in catalog.models:
        if m.name == model_name:
            return m
    return None


def _validate_dimensions(
    model: ExploreModel,
    joined_models: dict[str, ExploreModel],
    requested: list[str],
) -> list[tuple[str, str]]:
    """Validate and resolve dimension names to (table_alias, column_name) pairs.

    Dimensions can come from the base model or any joined model.
    Returns a list of (alias, column) tuples.
    """
    # Build a lookup: column_name -> (model_name, column_name)
    available: dict[str, str] = {}
    for dim in model.dimensions:
        available[dim.name] = model.name
    for jm_name, jm in joined_models.items():
        for dim in jm.dimensions:
            # Prefix with model name if ambiguous
            key = dim.name if dim.name not in available else f"{jm_name}.{dim.name}"
            available[key] = jm_name

    resolved: list[tuple[str, str]] = []
    for req in requested:
        if "." in req:
            # Explicit model.column reference
            parts = req.split(".", 1)
            resolved.append((parts[0], parts[1]))
        elif req in available:
            resolved.append((available[req], req))
        else:
            raise ValueError(f"Unknown dimension '{req}'. Available: {sorted(available.keys())}")
    return resolved


def _validate_metrics(
    model: ExploreModel,
    requested: list[str],
) -> list[Metric]:
    """Validate metric names against the model's metric definitions."""
    available = {m.name: m for m in model.metrics}
    resolved: list[Metric] = []
    for req in requested:
        if req not in available:
            raise ValueError(f"Unknown metric '{req}'. Available: {sorted(available.keys())}")
        resolved.append(available[req])
    return resolved


def build_sql(
    query: ExploreQuery,
    catalog: ExploreCatalog,
) -> tuple[str, dict]:
    """Build a parameterised SQL query from an ExploreQuery.

    Parameters
    ----------
    query:
        The explore query (dimensions, metrics, filters, sorts, limit).
    catalog:
        The full explore catalog (parsed from dbt YAML).

    Returns
    -------
    tuple of (sql_text, bind_params)

    Raises
    ------
    ValueError:
        If the requested model, dimensions, or metrics are not in the catalog.
    """
    # Find the base model
    base = _find_model(catalog, query.model)
    if base is None:
        raise ValueError(
            f"Unknown model '{query.model}'. Available: {[m.name for m in catalog.models]}"
        )

    # Resolve joined models needed for requested dimensions
    joined_models: dict[str, ExploreModel] = {}
    for jp in base.joins:
        jm = _find_model(catalog, jp.join_model)
        if jm:
            joined_models[jp.join_model] = jm

    # Validate dimensions and metrics
    dim_refs = _validate_dimensions(base, joined_models, query.dimensions)
    metric_defs = _validate_metrics(base, query.metrics)

    if not dim_refs and not metric_defs:
        raise ValueError("At least one dimension or metric must be selected.")

    # Build SELECT clause
    select_parts: list[str] = []
    select_aliases: list[str] = []

    for alias, col in dim_refs:
        select_parts.append(f"{alias}.{col}")
        select_aliases.append(col)

    for metric in metric_defs:
        agg_template = _AGG_SQL[metric.metric_type]
        agg_expr = agg_template.format(col=f"{base.name}.{metric.column}")
        select_parts.append(f"{agg_expr} AS {metric.name}")
        select_aliases.append(metric.name)

    # Build FROM clause — validate identifiers before interpolation
    if base.schema_name and not _SAFE_IDENT.match(base.schema_name):
        raise ValueError(f"Unsafe schema name: {base.schema_name!r}")
    if not _SAFE_IDENT.match(base.name):
        raise ValueError(f"Unsafe model name: {base.name!r}")
    schema_prefix = f"{base.schema_name}." if base.schema_name else ""
    from_clause = f"{schema_prefix}{base.name} AS {base.name}"

    # Track which joined tables are needed (dimensions + filters add to this)
    needed_joins: set[str] = {alias for alias, _ in dim_refs if alias != base.name}

    # Build lookup for resolving filter fields to their table alias
    filter_field_lookup: dict[str, str] = {}
    for dim in base.dimensions:
        filter_field_lookup[dim.name] = base.name
    for jm_name, jm in joined_models.items():
        for dim in jm.dimensions:
            if dim.name not in filter_field_lookup:
                filter_field_lookup[dim.name] = jm_name

    # Build WHERE clause
    bind_params: dict = {}
    where_parts: list[str] = []

    for i, flt in enumerate(query.filters):
        param_name = f"p{i}"
        if not _SAFE_IDENT.match(flt.field):
            raise ValueError(f"Unsafe filter field name: {flt.field!r}")

        # Resolve field to the correct table alias
        field_alias = filter_field_lookup.get(flt.field, base.name)
        # Ensure the join is included for this filter field
        if field_alias != base.name:
            needed_joins.add(field_alias)
        qualified_col = f"{field_alias}.{flt.field}"

        if flt.operator == "in":
            # IN clause with multiple values
            if isinstance(flt.value, list):
                placeholders = ", ".join(f":{param_name}_{j}" for j in range(len(flt.value)))
                where_parts.append(f"{qualified_col} IN ({placeholders})")
                for j, v in enumerate(flt.value):
                    bind_params[f"{param_name}_{j}"] = v
            else:
                where_parts.append(f"{qualified_col} = :{param_name}")
                bind_params[param_name] = flt.value
        elif flt.operator in _FILTER_OPS:
            template = _FILTER_OPS[flt.operator]
            where_parts.append(template.format(col=qualified_col, param=param_name))
            bind_params[param_name] = flt.value
        else:
            raise ValueError(f"Unknown filter operator '{flt.operator}'")

    # Build GROUP BY clause (only if we have both dims and metrics)
    group_by = ""
    if dim_refs and metric_defs:
        group_by = "GROUP BY " + ", ".join(f"{alias}.{col}" for alias, col in dim_refs)

    # Build ORDER BY clause
    order_parts: list[str] = []
    valid_fields = set(select_aliases)
    for sort in query.sorts:
        if sort.field in valid_fields:
            order_parts.append(f"{sort.field} {sort.direction.value}")

    if not order_parts and metric_defs:
        # Default: sort by first metric descending
        order_parts.append(f"{metric_defs[0].name} DESC")

    order_by = "ORDER BY " + ", ".join(order_parts) if order_parts else ""

    # Build JOIN clauses (includes joins needed by dimensions AND filters)
    join_clauses: list[str] = []
    for jp in base.joins:
        if jp.join_model in needed_joins:
            jm = joined_models[jp.join_model]
            if not _SAFE_IDENT.match(jp.join_model):
                raise ValueError(f"Unsafe join model name: {jp.join_model!r}")
            if jm.schema_name and not _SAFE_IDENT.match(jm.schema_name):
                raise ValueError(f"Unsafe join schema name: {jm.schema_name!r}")
            jm_schema = f"{jm.schema_name}." if jm.schema_name else ""
            on_clause = _resolve_join_on(jp.sql_on, base.name, jp.join_model)
            join_clauses.append(
                f"LEFT JOIN {jm_schema}{jp.join_model} AS {jp.join_model} ON {on_clause}"
            )

    # Assemble the SQL
    sql_parts = [
        "SELECT " + ",\n       ".join(select_parts),
        f"FROM {from_clause}",
    ]
    sql_parts.extend(join_clauses)
    if where_parts:
        sql_parts.append("WHERE " + "\n  AND ".join(where_parts))
    if group_by:
        sql_parts.append(group_by)
    if order_by:
        sql_parts.append(order_by)
    sql_parts.append("LIMIT :_limit")
    bind_params["_limit"] = query.limit

    sql = "\n".join(sql_parts)

    log.info(
        "sql_built",
        model=query.model,
        dimensions=len(dim_refs),
        metrics=len(metric_defs),
        filters=len(query.filters),
    )

    return sql, bind_params
