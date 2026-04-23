# Using the DataPulse Graph MCP

> Call the `datapulse-graph` MCP tools **before** changing shared code to see blast radius and test coverage.

## When to use (MANDATORY)

### Before editing any symbol
```
dp_context(symbol_name) -> see callers, callees, tests, layer
```

### Before refactoring or renaming
```
dp_impact(symbol_name, max_depth=3) -> blast radius across layers
```

### Before creating PRs or commits
```
dp_detect_changes() -> maps git diff to affected symbols
```

### When searching for symbols
```
dp_query(query, kind?, layer?) -> find symbols by name
```

Filter `kind`: function, class, method, hook, component, page, dbt_model, dbt_source, test, api_endpoint, module.
Filter `layer`: bronze, silver, gold, api, frontend, test, backend.

## High-impact symbols (change with extra care)

| Symbol | Blast radius | Layers |
|--------|-------------|--------|
| `apply_filters` | 160 symbols | gold, backend, api, bronze |
| `stg_sales` (dbt) | 55 symbols | gold (6 dims, 1 fact, 8 aggs, 8 features), api, backend |
| `cache_get` / `cache_set` | all cached routes | backend, api |
| `AnalyticsRepository` | 40+ API endpoints | gold, api, frontend |

## Duplication patterns to consolidate

- `_set_cache` duplicated across 7 route files (analytics, anomalies, branding, forecasting, gamification, reseller, targets).

## Layer boundaries (cached)

- **bronze**: loader.py, reader.py, column_map.py, pipeline executor
- **silver**: stg_sales (single staging model)
- **gold**: 6 dims + 1 fact + 8 aggs + 8 features (all dbt models)
- **api**: 28 routers, 40+ analytics endpoints, filters, auth, deps
- **frontend**: 12 dashboard components, 60+ hooks, 22+ pages
- **test**: 50+ test functions across analytics, auth, cache, pipeline

## Example workflow

```
# Task: Fix LIKE wildcard injection in apply_filters

# 1. Check blast radius first
dp_impact("apply_filters", max_depth=2)
# -> 160 affected symbols. Proceed carefully.

# 2. Check which tests already exist
dp_context("apply_filters")
# -> test_build_where_*, test_analytics_repository.*

# 3. Apply the fix (escape wildcards)

# 4. Verify nothing unintended moved
dp_detect_changes()
# -> confirms only filters.py changed; shows downstream impact.
```

## Do NOT skip graph checks when touching

- `queries.py` (shared SQL builders)
- `filters.py` (used by ALL analytics)
- `cache.py` / `cache_decorator.py` (used by 7+ routes)
- `auth.py` / `jwt.py` / `deps.py` (auth chain)
- Any dbt model (cascades through medallion layers)
- `repository.py` or `service.py` in analytics (40+ endpoints)
