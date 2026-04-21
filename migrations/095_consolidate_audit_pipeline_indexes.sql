-- Migration 095: Consolidate indexes on audit_log + pipeline_runs
-- Layer: Application / Observability
-- Idempotent: safe to run multiple times (DROP/CREATE IF [NOT] EXISTS).
--
-- Why:
--   Both tables are scanned with the pattern "WHERE tenant_id = X ORDER BY
--   <time> DESC" (and sometimes + status). The existing single-column
--   indexes force a bitmap-AND or scan-one-then-filter — neither can
--   return tenant-scoped rows in time order without a sort step.
--
--   A composite (tenant_id, <time> DESC [, status]) lets the planner
--   walk straight to the tenant slice in descending time order with
--   no sort and no filter evaluation per row.
--
-- Changes:
--   audit_log:
--     + idx_audit_log_tenant_created_at  (tenant_id, created_at DESC)
--     - idx_audit_log_tenant_id          (single col, covered by new composite)
--     - idx_audit_log_created_at         (single col, covered by new composite)
--     + idx_audit_log_action_created_at  (action, created_at DESC)  replaces
--     - idx_audit_log_action             (low-cardinality alone; near-useless)
--   pipeline_runs:
--     + idx_pipeline_runs_tenant_started_status  (tenant_id, started_at DESC, status)
--     - idx_pipeline_runs_tenant_status          (covered by new composite)
--     - idx_pipeline_runs_started_at             (covered by new composite)
--     (keeps idx_pipeline_runs_run_type — queried alone in service layer)
--
-- Rollback:
--   Each CREATE has a matching DROP IF EXISTS and vice-versa; re-running
--   prior migrations 005/008/014 restores the original indexes.

BEGIN;

-- ============================================================
-- audit_log — composite (tenant_id, created_at DESC)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_created_at
    ON public.audit_log (tenant_id, created_at DESC);

DROP INDEX IF EXISTS public.idx_audit_log_tenant_id;
DROP INDEX IF EXISTS public.idx_audit_log_created_at;

-- ============================================================
-- audit_log — replace bare (action) with (action, created_at DESC)
-- Low-cardinality columns alone are rarely selective; pairing with
-- created_at makes "show recent rows for action X" efficient.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_audit_log_action_created_at
    ON public.audit_log (action, created_at DESC);

DROP INDEX IF EXISTS public.idx_audit_log_action;

-- ============================================================
-- pipeline_runs — composite (tenant_id, started_at DESC, status)
-- Covers both "recent runs for tenant" and "recent runs by status"
-- without a separate index per access pattern.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_tenant_started_status
    ON public.pipeline_runs (tenant_id, started_at DESC, status);

DROP INDEX IF EXISTS public.idx_pipeline_runs_tenant_status;
DROP INDEX IF EXISTS public.idx_pipeline_runs_started_at;

-- Note: idx_pipeline_runs_run_type is KEPT — pipeline/repository.py queries
-- on run_type alone (e.g. "latest full run"). Low cardinality but the
-- composite above does not lead with run_type, so a dedicated index is
-- still the cheapest path for that access pattern.

COMMIT;
