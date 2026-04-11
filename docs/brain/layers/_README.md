# Layers

Notes about each medallion layer in the DataPulse architecture.

## Planned Contents

| File | Layer | Description |
|------|-------|-------------|
| `bronze.md` | Bronze | Raw data ingestion — loader, column_map, import_pipeline |
| `silver.md` | Silver | Cleaned/deduplicated — dbt staging models |
| `gold.md` | Gold | Aggregated metrics — dbt marts, dims, facts, aggs |
| `api.md` | API | FastAPI routes, services, repositories |
| `frontend.md` | Frontend | Next.js dashboard, components, hooks |

Session notes already generate `[[wikilinks]]` to these layer names.
The graph will auto-connect once these files exist.
