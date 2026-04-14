# Pharmaceutical Platform Expansion — Session Prompts

> Copy-paste each prompt into a fresh Claude Code session to execute.
> Each prompt is self-contained — the agent needs no prior conversation context.

---

## Session 1: Foundation

```
Read `docs/pharma-expansion/sessions/session-1-foundation.md` for the full spec, then execute it.

You are building the foundation for a pharmaceutical platform expansion of DataPulse. This session creates shared infrastructure that ALL subsequent sessions depend on.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Create 10 database migrations (050-059) in `migrations/` — follow the exact pattern from migration 049. All tables need ENABLE + FORCE RLS, idempotent DO $$ policy guards, indexes, GRANT SELECT to datapulse_reader.
2. Update `src/datapulse/billing/plans.py` — add 8 new PlanLimits fields (inventory_management, expiry_tracking, dispensing_analytics, purchase_orders, pos_integration, max_stock_items, max_suppliers, stock_alerts) with correct tier defaults.
3. Create `src/datapulse/bronze/base_loader.py` — abstract BronzeLoader ABC with template method pattern (discover -> read -> validate -> load).
4. Create `src/datapulse/bronze/registry.py` — loader registry dict.
5. Add `feature_platform: bool = False` to Settings in config.py.
6. Create `dbt/models/bronze/_bronze__inventory_sources.yml` — source definitions for 7 new bronze tables.
7. Create 7 bronze view models in `dbt/models/bronze/` — follow `bronze_sales.sql` pattern exactly.
8. Write tests: `tests/test_billing_plans_platform.py`, `tests/test_base_loader.py`.

After completing, run verification:
- pytest tests/test_billing_plans_platform.py tests/test_base_loader.py -v
- cd dbt && dbt compile --select source:bronze.*
- pytest tests/ -x --timeout=120
- ruff check src/ tests/
```

---

## Session 2: Inventory Core

```
Read `docs/pharma-expansion/sessions/session-2-inventory-core.md` for the full spec, then execute it.

You are building the complete inventory data pipeline for DataPulse. Session 1 already created the bronze tables (stock_receipts, stock_adjustments, inventory_counts), the BronzeLoader ABC, and billing tier flags.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Create 3 column map + loader pairs: receipts, adjustments, counts — each extending BronzeLoader.
2. Create 3 dbt staging models: stg_stock_receipts, stg_stock_adjustments, stg_inventory_counts — follow stg_sales.sql pattern (incremental, delete+insert, dedup, RLS post_hook).
3. Create fct_stock_movements — UNION of receipts + adjustments + sales outflow (from fct_sales) + returns. This is the central inventory fact table. MD5 surrogate key, LEFT JOIN dims with COALESCE -1 fallback.
4. Create fct_inventory_counts — physical count records with dim joins.
5. Create agg_stock_levels (SUM movements = current stock), agg_stock_valuation (weighted avg cost), agg_stock_reconciliation (counted vs calculated).
6. Create `src/datapulse/inventory/` module: models.py (frozen Pydantic), repository.py (parameterized SQL), service.py (caching).
7. Create `src/datapulse/api/routes/inventory.py` — 10 endpoints with plan gating + RBAC.
8. Wire in deps.py and app.py (behind feature_platform flag).
9. Write tests for all new code (95%+ coverage).

After completing, run verification:
- pytest tests/test_inventory_*.py tests/test_receipts_loader.py tests/test_adjustments_loader.py -v
- cd dbt && dbt compile --select stg_stock_receipts stg_stock_adjustments stg_inventory_counts fct_stock_movements fct_inventory_counts agg_stock_levels agg_stock_valuation agg_stock_reconciliation
- pytest tests/ -x --timeout=120
- ruff check src/ tests/
```

---

## Session 3: Expiry & Batch Tracking

```
Read `docs/pharma-expansion/sessions/session-3-expiry-batches.md` for the full spec, then execute it.

You are building the batch/lot tracking dimension, expiry alerts, and FEFO enforcement for DataPulse. Session 1 created bronze.batches table. Session 2 created fct_stock_movements and agg_stock_levels.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Create batches column map + ExcelBatchesLoader.
2. Create stg_batches staging model (incremental, dedup, RLS).
3. Create dim_batch — MD5 surrogate key, SCD Type 1, -1 Unknown row on full refresh, computed_status (expired/near_expiry/active based on days to expiry). Follow dim_product.sql pattern exactly.
4. Create fct_batch_status (lifecycle events), agg_expiry_summary (counts by status per site), feat_expiry_alerts (30/60/90 day thresholds).
5. Create `src/datapulse/expiry/fefo.py` — FEFO batch selection algorithm (First Expiry First Out).
6. Create `src/datapulse/expiry/` module: models.py, repository.py, service.py — including quarantine and write-off flows.
7. Create `src/datapulse/api/routes/expiry.py` — 8 endpoints with plan gating + RBAC.
8. Wire in deps.py and app.py.
9. Write tests including thorough FEFO algorithm tests.

After completing, run verification:
- pytest tests/test_expiry_*.py tests/test_fefo.py tests/test_batches_loader.py -v
- cd dbt && dbt compile --select stg_batches dim_batch fct_batch_status agg_expiry_summary feat_expiry_alerts
- pytest tests/ -x --timeout=120
- ruff check src/ tests/
```

---

## Session 4: Purchase Orders & Suppliers

```
Read `docs/pharma-expansion/sessions/session-4-purchase-orders.md` for the full spec, then execute it.

You are building the PO workflow, supplier management, and margin analysis for DataPulse. Session 1 created bronze tables for suppliers, purchase_orders, po_lines. Session 2 created fct_stock_movements (PO receipts should feed into it).

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Create suppliers + PO column maps and 2 loaders (ExcelSuppliersLoader, ExcelPOLoader).
2. Create 3 staging models: stg_suppliers, stg_purchase_orders, stg_po_lines.
3. Create dim_supplier (MD5 key, SCD1, -1 Unknown row).
4. Create fct_purchase_orders (header-level) and fct_po_lines (line-level with dim joins).
5. Create agg_margin_analysis (COGS from PO unit prices vs sales revenue) and agg_supplier_performance (avg lead time, fill rate).
6. Create `src/datapulse/purchase_orders/` and `src/datapulse/suppliers/` modules — full Route->Service->Repository for each.
7. CRITICAL: PO receive endpoint must create bronze.stock_receipts entries that flow through to fct_stock_movements.
8. Create API routes: 7 PO endpoints + 5 supplier endpoints + 1 margin analysis.
9. Wire in deps.py and app.py.
10. Write tests (especially PO receive -> stock receipt creation flow).

After completing, run verification:
- pytest tests/test_po_*.py tests/test_suppliers_*.py -v
- cd dbt && dbt compile --select stg_suppliers stg_purchase_orders stg_po_lines dim_supplier fct_purchase_orders fct_po_lines agg_margin_analysis agg_supplier_performance
- pytest tests/ -x --timeout=120
- ruff check src/ tests/
```

---

## Session 5: Dispensing Analytics

```
Read `docs/pharma-expansion/sessions/session-5-dispensing-analytics.md` for the full spec, then execute it.

You are building derived dispensing analytics for DataPulse. These are mostly dbt feature models reading from existing aggs. Session 2 created agg_stock_levels + agg_sales_daily. Session 3 created feat_expiry_alerts. Session 1 created public.reorder_config table.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Create 5 dbt feature models:
   - feat_dispense_rate — avg qty/day from agg_sales_daily (last 90 days)
   - feat_days_of_stock — current_stock / avg_daily_dispense
   - feat_product_velocity — extends feat_product_lifecycle with fast/slow/dead classification
   - feat_stockout_risk — products where days_of_stock < reorder_lead_days
   - feat_reorder_alerts — products below reorder_point
2. Add reorder_config as a dbt source (it's an app table, not dbt-managed).
3. Create `src/datapulse/dispensing/` module: models.py, repository.py, service.py.
4. Create `src/datapulse/api/routes/dispensing.py` — 5 endpoints.
5. Create reorder config CRUD: `src/datapulse/inventory/reorder_repository.py` + `reorder_service.py` — validate min_stock <= reorder_point <= max_stock.
6. Wire in deps.py and app.py.
7. Write tests.

After completing, run verification:
- pytest tests/test_dispensing_*.py tests/test_reorder_config.py -v
- cd dbt && dbt compile --select feat_dispense_rate feat_days_of_stock feat_product_velocity feat_stockout_risk feat_reorder_alerts
- pytest tests/ -x --timeout=120
- ruff check src/ tests/
```

---

## Session 6: Frontend — Inventory + Expiry

```
Read `docs/pharma-expansion/sessions/session-6-frontend-inventory-expiry.md` for the full spec, then execute it.

You are building frontend pages for the Inventory and Expiry domains of DataPulse. Backend APIs are complete (Sessions 2+3). The frontend uses Next.js 14 + TypeScript + Tailwind + SWR + Recharts + dark/light theme via next-themes.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Add "Operations" nav group to `frontend/src/lib/constants.ts` — with items for Inventory, Dispensing, Expiry, Purchase Orders, Suppliers. Gate behind NEXT_PUBLIC_FEATURE_PLATFORM env var.
2. Create TypeScript types: `frontend/src/types/inventory.ts`, `frontend/src/types/expiry.ts`.
3. Create 10 SWR hooks following existing pattern (useSWR + swrKey + fetchAPI).
4. Create inventory pages: /inventory (dashboard with KPIs, stock table, movement chart, reorder alerts) + /inventory/[drug_code] (product detail with stock history, movements, batches, reorder config form).
5. Create expiry page: /expiry (calendar view, near-expiry list with 30/60/90 tabs, expired stock table, write-off chart).
6. Create loading.tsx for each page.
7. Create 11 components — all charts must use ChartCard + useChartTheme() for dark/light support.

After completing, run verification:
- cd frontend && npx tsc --noEmit
- cd frontend && npm run build
```

---

## Session 7: Frontend — PO + Dispensing + Suppliers

```
Read `docs/pharma-expansion/sessions/session-7-frontend-po-dispensing.md` for the full spec, then execute it.

You are building frontend pages for Purchase Orders, Suppliers, and Dispensing Analytics. Backend APIs are complete (Sessions 4+5). Session 6 already added the Operations nav group and established the component patterns.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Create TypeScript types: purchase-orders.ts, suppliers.ts, dispensing.ts.
2. Create ~11 SWR hooks (PO list, PO detail, PO create mutation, suppliers, supplier performance, dispense rate, days of stock, velocity, stockout risk, reconciliation).
3. Create pages:
   - /purchase-orders — PO list with status badges + create form
   - /purchase-orders/[po_number] — PO detail with status pipeline (draft->submitted->partial->received) + line items with progress bars
   - /suppliers — searchable table + performance chart
   - /dispensing — dispense rate cards, days-of-stock chart, velocity 4-quadrant grid, stockout risk table, reconciliation summary
4. Create loading.tsx for each page.
5. Create ~14 components — all charts use ChartCard + useChartTheme.

After completing, run verification:
- cd frontend && npx tsc --noEmit
- cd frontend && npm run build
```

---

## Session 8: Integration Tests + E2E + Polish

```
Read `docs/pharma-expansion/sessions/session-8-integration-e2e.md` for the full spec, then execute it.

All backend domains and frontend pages are complete (Sessions 1-7). This session writes cross-domain integration tests, Playwright E2E tests, and adds polish (empty states, upload route extension).

NOTE: POS integration is being designed separately by a team partner.

IMPORTANT: Read `CLAUDE.md` first for project conventions, then read the session spec file above.

Your deliverables:
1. Write 4 cross-domain integration tests:
   - test_integration_inventory_flow.py — receipt -> stock movement -> stock level -> reorder alert
   - test_integration_po_receipt_flow.py — PO -> receive -> stock receipt -> margin analysis
   - test_integration_expiry_flow.py — batch -> near-expiry alert -> quarantine -> write-off
   - test_integration_dispensing_flow.py — sales -> dispense rate -> days of stock -> stockout risk
2. Extend upload route to accept inventory Excel files (detect file type from headers, use loader registry).
3. Write 5 Playwright E2E specs (inventory, expiry, purchase-orders, dispensing, suppliers).
4. Create 3 empty state components for when no data exists.
5. Write upload route tests.

After completing, run verification:
- pytest tests/test_integration_*.py -v
- pytest tests/ -x --timeout=120 --cov=src/datapulse --cov-fail-under=95
- cd frontend && npm run build
- cd frontend && npx playwright test
- ruff check src/ tests/
```
