-- Migration 097: Per-table autovacuum tuning for POS write-hot tables
-- Layer: POS operational
-- Idempotent: storage parameters are ALTER TABLE SET — safe to re-run.
--
-- Why:
--   Migration 034 tuned autovacuum for the medallion tables (bronze.sales,
--   pipeline_runs, audit_log, etc.) but did not cover the POS schema, which
--   has become the highest-churn part of the database:
--
--     pos.transactions       — INSERT on every checkout; UPDATE on status
--                              transitions (draft → completed → voided/returned)
--     pos.transaction_items  — ~5x the volume of pos.transactions (append-mostly)
--     pos.receipts           — ~1:1 with completed transactions
--     pos.shift_records      — INSERT on open, UPDATE on close/adjust
--     pos.idempotency_keys   — INSERT + DELETE churn (keys expire rapidly)
--
--   Default autovacuum_vacuum_scale_factor=0.2 (20%) is far too lax for
--   these tables: a busy tenant can rack up hundreds of thousands of dead
--   tuples before the threshold is hit, bloating indexes and slowing the
--   planner.
--
-- Values mirror migration 034's approach: 1-5% scale factor on vacuum,
-- 0.5-2% on analyze, and a short vacuum_cost_delay to reduce live-query
-- impact during bursts.
--
-- Rollback: ALTER TABLE <t> RESET (autovacuum_vacuum_scale_factor,
-- autovacuum_analyze_scale_factor, autovacuum_vacuum_cost_delay);

BEGIN;

-- pos.transactions: checkout header — INSERT + status UPDATEs
ALTER TABLE pos.transactions SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_delay    = 5
);

-- pos.transaction_items: ~5x volume of transactions, append-mostly
ALTER TABLE pos.transaction_items SET (
    autovacuum_vacuum_scale_factor  = 0.02,
    autovacuum_analyze_scale_factor = 0.01,
    autovacuum_vacuum_cost_delay    = 10
);

-- pos.receipts: ~1:1 with completed transactions, append-mostly
ALTER TABLE pos.receipts SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_delay    = 10
);

-- pos.shift_records: INSERT on open + UPDATE on close/adjust — moderate churn
ALTER TABLE pos.shift_records SET (
    autovacuum_vacuum_scale_factor  = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- pos.idempotency_keys: INSERT + DELETE churn as keys expire. Aggressive
-- vacuum keeps HOT-update chains short and prevents index bloat.
ALTER TABLE pos.idempotency_keys SET (
    autovacuum_vacuum_scale_factor  = 0.01,
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_cost_delay    = 5
);

COMMIT;
