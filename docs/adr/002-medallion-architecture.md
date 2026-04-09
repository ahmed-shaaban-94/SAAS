# ADR-002: Medallion data architecture with dbt + PostgreSQL

**Status**: Accepted  
**Date**: 2026-04-09  
**Deciders**: Pipeline Engineer, Analytics Engineer

## Context

DataPulse ingests raw Excel/CSV files from pharmacy/retail ERPs. The data arrives with:
- Inconsistent column names across source systems
- Duplicated rows (same invoice imported multiple times)
- Mixed types (dates as strings, amounts with currency symbols)
- No tenant isolation — all tenants share the same source format

The analytics layer needs clean, consistent, aggregated data that can be queried sub-second for 1M+ row datasets.

## Decision

Adopt a three-layer **medallion architecture**:

```
Excel/CSV → Bronze (raw) → Silver (clean, deduped) → Gold/Marts (aggregated)
```

| Layer | Schema | Technology | Responsibility |
|-------|--------|-----------|---------------|
| Bronze | `bronze` | Python (Polars + PyArrow) | Load raw files as-is, minimal transformation |
| Silver | `public_staging` | dbt staging models | Dedup, type-cast, rename, RLS |
| Gold | `public_marts` | dbt mart models | Aggregations: 6 dims + 1 fact + 8 aggs |

**Key choices:**
- **Polars** for bronze ingestion: columnar in-memory processing, 10x faster than pandas for 2M-row loads
- **dbt** for silver→gold: SQL-first transformations with version control, testing, and documentation
- **PostgreSQL views with RLS** for silver layer: `security_invoker=on` propagates caller's tenant context
- **Parquet as intermediary**: Bronze loader writes to Parquet before PostgreSQL for restart safety

## Consequences

**Good:**
- Bronze is immutable — raw data is never lost, re-ingestion is safe
- dbt tests catch data quality regressions (null rates, referential integrity, value ranges)
- Gold aggregations pre-compute expensive JOINs — dashboard queries run in <100ms
- Tenant isolation enforced at the DB layer (RLS), not application code

**Risks/trade-offs:**
- Two-phase ingestion (Polars → dbt) adds latency vs. direct SQL load
- dbt requires a full `dbt run` after schema changes — not suitable for real-time streaming
- Gold aggregations need rebuilding when source data changes (mitigated by incremental dbt models)
