-- Migration 032: Per-table autovacuum tuning for high-write tables
--
-- Problem: PostgreSQL's default autovacuum_vacuum_scale_factor = 0.2 (20%)
-- means autovacuum only fires when 20% of a table's rows are dead tuples.
-- For large/frequently updated tables this causes significant bloat:
--   - bronze.sales (2.27M rows): 454K dead rows before any cleanup
--   - pipeline_runs + quality_checks: heavy write traffic during ingestion
--   - audit_log: append-heavy, needs fast ANALYZE to keep stats fresh
--
-- Fix: Override per-table with lower scale_factor (1-5% threshold) and
-- increase vacuum cost delay slightly to reduce I/O impact during peak queries.
--
-- These are storage parameters — no data changes, safe to apply live.
-- Rollback: ALTER TABLE <t> RESET (autovacuum_vacuum_scale_factor, ...);

BEGIN;

-- bronze.sales: 2.27M rows, heavy append-only ingestion
-- Trigger vacuum at 1% (22k rows) instead of default 454k rows
ALTER TABLE bronze.sales SET (
    autovacuum_vacuum_scale_factor    = 0.01,
    autovacuum_analyze_scale_factor   = 0.005,
    autovacuum_vacuum_cost_delay      = 10
);

-- pipeline_runs: frequent INSERT + UPDATE (status transitions)
ALTER TABLE public.pipeline_runs SET (
    autovacuum_vacuum_scale_factor    = 0.05,
    autovacuum_analyze_scale_factor   = 0.02,
    autovacuum_vacuum_cost_delay      = 5
);

-- quality_checks: one row per stage per run, heavy write during ingestion
ALTER TABLE public.quality_checks SET (
    autovacuum_vacuum_scale_factor    = 0.05,
    autovacuum_analyze_scale_factor   = 0.02,
    autovacuum_vacuum_cost_delay      = 5
);

-- audit_log: append-only but large volume; keep stats fresh for query planner
ALTER TABLE public.audit_log SET (
    autovacuum_vacuum_scale_factor    = 0.02,
    autovacuum_analyze_scale_factor   = 0.01,
    autovacuum_vacuum_cost_delay      = 10
);

-- anomaly_alerts: time-series inserts + status updates
ALTER TABLE public.anomaly_alerts SET (
    autovacuum_vacuum_scale_factor    = 0.05,
    autovacuum_analyze_scale_factor   = 0.02
);

COMMIT;
