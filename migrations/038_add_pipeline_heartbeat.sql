-- Migration: Add heartbeat_at column to pipeline_runs
-- Purpose: Detect stale/abandoned pipeline runs when a worker dies mid-execution.
--          The scheduler periodically checks for runs stuck in "running" status
--          with heartbeat_at older than 10 minutes and marks them as failed.
--
-- Run order: after 037_fix_rls_owner_policies.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS guard)

-- ============================================================
-- 1. Add heartbeat_at column (nullable — old runs won't have it)
-- ============================================================
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

-- ============================================================
-- 2. Index for stale run detection query
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_heartbeat_stale
    ON public.pipeline_runs(status, heartbeat_at)
    WHERE status = 'running';

-- ============================================================
-- 3. Comment
-- ============================================================
COMMENT ON COLUMN public.pipeline_runs.heartbeat_at IS
    'Last heartbeat timestamp — updated between pipeline stages. '
    'Stale runs (heartbeat_at > 10 min old) are marked failed by the scheduler.';
