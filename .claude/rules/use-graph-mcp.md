# Rule: Use DataPulse Graph MCP for Precision Work

## When to Use Graph MCP (MANDATORY)

Use the `datapulse-graph` MCP tools **before** making changes in any of these scenarios:

### 1. Before Editing Any Symbol
```
dp_context(symbol_name) -> see callers, callees, tests, layer
```
- Check WHO calls this function/class/component
- Check WHAT tests cover it
- Check which layer it belongs to (bronze/silver/gold/api/frontend/test)

### 2. Before Refactoring or Renaming
```
dp_impact(symbol_name, max_depth=3) -> blast radius analysis
```
- See ALL downstream affected symbols across layers
- Understand the medallion-layer cascade (bronze -> silver -> gold -> API -> frontend)
- Decide if the change is safe or needs coordination

### 3. Before Creating PRs or Commits
```
dp_detect_changes() -> maps git diff to affected symbols
```
- Validates your changes haven't missed any affected dependencies
- Shows symbols in changed files and their downstream impact

### 4. When Searching for Symbols
```
dp_query(query, kind?, layer?) -> find symbols by name
```
- Use `kind` filter: function, class, method, hook, component, page, dbt_model, dbt_source, test, api_endpoint, module
- Use `layer` filter: bronze, silver, gold, api, frontend, test, backend

## Key Graph Insights (Cached Knowledge)

### High-Impact Symbols (Change with Extra Care)
| Symbol | Blast Radius | Layers Affected |
|--------|-------------|-----------------|
| `apply_filters` | 160 symbols | gold, backend, api, bronze |
| `stg_sales` (dbt) | 55 symbols | gold (6 dims, 1 fact, 8 aggs, 8 features), api, backend |
| `cache_get/set` | All cached routes | backend, api |
| `AnalyticsRepository` | 40+ API endpoints | gold, api, frontend |

### Duplication Patterns to Consolidate
- `_set_cache` duplicated in 7 route files (analytics, anomalies, branding, forecasting, gamification, reseller, targets)

### Layer Boundaries
- **bronze**: loader.py, reader.py, column_map.py, pipeline executor
- **silver**: stg_sales (dbt model, single staging model)
- **gold**: 6 dims + 1 fact + 8 aggs + 8 features (all dbt models)
- **api**: 28 routers, 40+ analytics endpoints, filters, auth, deps
- **frontend**: 12 dashboard components, 60+ hooks, 22+ pages
- **test**: 50+ test functions across analytics, auth, cache, pipeline

## Example Workflow

```
# Task: Fix LIKE wildcard injection in apply_filters

# Step 1: Check blast radius FIRST
dp_impact("apply_filters", max_depth=2)
# Result: 160 affected symbols! Be careful.

# Step 2: Check what tests exist
dp_context("apply_filters")
# Result: tested by test_build_where_*, test_analytics_repository.*

# Step 3: Make the fix (escape wildcards)

# Step 4: Verify no unintended changes
dp_detect_changes()
# Result: confirms only filters.py changed, shows downstream impact
```

## Do NOT Skip Graph Checks When:
- Touching `queries.py` (shared SQL builders)
- Touching `filters.py` (used by ALL analytics)
- Touching `cache.py` / `cache_decorator.py` (used by 7+ routes)
- Touching `auth.py` / `jwt.py` / `deps.py` (auth chain)
- Touching any dbt model (cascades through medallion layers)
- Touching `repository.py` or `service.py` in analytics (40+ endpoints)
