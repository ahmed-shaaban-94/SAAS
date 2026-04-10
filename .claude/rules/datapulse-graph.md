# DataPulse Dependency Graph Rules

These rules describe the module dependency constraints for the DataPulse codebase.
Violations should be fixed before merging.

## Layer Ordering (no upward imports)

```
api  ->  analytics / pipeline / forecasting / billing / ai_light / explore
         |
         v
     core / cache / config
         |
         v
   bronze / import_pipeline
```

- **api/** may import from any business layer, core, and config.
- **analytics/**, **pipeline/**, **forecasting/**, **billing/**, **ai_light/**, **explore/** may import from `core/`, `cache`, and `config` — never from `api/`.
- **core/** and **cache** may only import from `config`.
- **bronze/** and **import_pipeline/** are leaf modules — they import only from `config` and stdlib/third-party.
- No circular imports between business modules (e.g. analytics must not import pipeline and vice versa).

## Route -> Service -> Repository

Every API route follows a strict three-layer pattern:

1. **Route** (`api/routes/*.py`) — HTTP handling, validation, auth. Calls service only.
2. **Service** (`<module>/service.py`) — business logic, caching, orchestration. Calls repository only.
3. **Repository** (`<module>/repository.py`) — raw SQL queries via SQLAlchemy. No business logic.

Rules:
- Routes must NOT import repositories directly.
- Repositories must NOT import services.
- Services must NOT import route modules.

## Dependency Injection

- All database sessions come through `api/deps.py` via FastAPI `Depends()`.
- Use `get_tenant_session` (authenticated, RLS-scoped) — never `get_db_session` (deprecated).
- Service factories live in `deps.py` and wire repository -> service.

## Frontend Component Graph

```
pages  ->  components  ->  hooks  ->  lib (api, auth, utils)
```

- **Pages** (`app/dashboard/*/page.tsx`) import components and hooks.
- **Components** (`components/**/*.tsx`) import hooks and lib utilities.
- **Hooks** (`hooks/*.ts`) import from `lib/` only.
- **lib/** contains pure utilities — no React imports except in `swr-config.ts`.
- Components must not import pages. Hooks must not import components.

## dbt Model Graph

```
sources (bronze)  ->  staging (silver)  ->  dims + fact (gold)  ->  aggs (gold)
```

- **Staging** models (`stg_*`) reference only `source()` macros.
- **Dimension** and **fact** models reference staging via `ref('stg_*')`.
- **Aggregation** models reference dims/fact via `ref()` — never staging or source directly.
- All models must be declared in a `schema.yml` with at least `unique_key` and `not_null` tests.

## Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Python module | `snake_case` | `analytics/service.py` |
| API route | `kebab-case` URL | `/api/v1/sales-summary` |
| dbt model | `snake_case` prefixed | `stg_sales`, `dim_customer`, `agg_sales_daily` |
| Frontend component | `PascalCase` file | `KpiGrid.tsx` |
| Frontend hook | `camelCase` with `use` prefix | `useSalesSummary.ts` |
| Test file | `test_<module>.py` / `*.spec.ts` | `test_analytics.py`, `dashboard.spec.ts` |
