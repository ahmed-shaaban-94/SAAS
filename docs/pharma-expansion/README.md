# Pharmaceutical Platform Expansion — Blueprint

## Overview

Transforms DataPulse from a pharma sales analytics tool into a complete pharmaceutical operations platform with 5 new domains.

## Session Build Order

```
Session 1 (Foundation)
  |
  +-- Session 2 (Inventory Core) ---+
  |                                  |
  +-- Session 3 (Expiry & Batches) -+-- Session 5 (Dispensing Analytics)
  |                                  |
  +-- Session 4 (Purchase Orders) --+
  |
  +-- Session 6 (Frontend: Inventory + Expiry)
  |
  +-- Session 7 (Frontend: PO + Dispensing + Suppliers)
  |
  +-- Session 8 (Integration Tests + E2E + Polish)
  |
  +-- POS Session (Separate — handled by team partner)
```

## Sessions

| # | Focus | Depends On | Est. Files | Prompt |
|---|-------|-----------|-----------|--------|
| 1 | Foundation: migrations, billing, loader interface, permissions | None | ~25 | [session-1-foundation.md](sessions/session-1-foundation.md) |
| 2 | Inventory Core: loaders, staging, facts, aggs, API | S1 | ~30 | [session-2-inventory-core.md](sessions/session-2-inventory-core.md) |
| 3 | Expiry & Batches: dim_batch, FEFO, alerts, API | S1 | ~23 | [session-3-expiry-batches.md](sessions/session-3-expiry-batches.md) |
| 4 | Purchase Orders & Suppliers: PO workflow, margins, API | S1 | ~34 | [session-4-purchase-orders.md](sessions/session-4-purchase-orders.md) |
| 5 | Dispensing Analytics: derived features, stockout risk, API | S2+S3 | ~20 | [session-5-dispensing-analytics.md](sessions/session-5-dispensing-analytics.md) |
| 6 | Frontend: Inventory + Expiry pages | S2+S3 | ~33 | [session-6-frontend-inventory-expiry.md](sessions/session-6-frontend-inventory-expiry.md) |
| 7 | Frontend: PO + Dispensing + Suppliers pages | S4+S5 | ~33 | [session-7-frontend-po-dispensing.md](sessions/session-7-frontend-po-dispensing.md) |
| 8 | Integration Tests + E2E + Polish | S1-S7 | ~15 | [session-8-integration-e2e.md](sessions/session-8-integration-e2e.md) |

Sessions 2, 3, 4 can run **in parallel** after Session 1.

## Totals

- 9 new database tables + 10 migrations
- 33 new dbt models (7 staging, 2 dims, 5 facts, 6 aggs, 6 features, 7 bronze views)
- ~15 new Python modules with ~35 API endpoints
- 9 new frontend pages + ~25 components + ~18 hooks
- ~30 test files

## Reference

- Full blueprint: [../../.claude/plans/linked-jingling-puppy.md](../../.claude/plans/linked-jingling-puppy.md)
