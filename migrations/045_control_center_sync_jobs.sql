-- Migration: 045 — Control Center: sync_jobs (thin overlay on pipeline_runs)
-- Layer: application / control_center
-- Phase: Control Center Phase 1a (Foundation)
--
-- Run order: after 044_control_center_workflow.sql
-- Idempotent: safe to run multiple times
--
-- What this does:
--   1. Creates sync_jobs — a Control-Center-specific overlay that adds
--      (connection_id, release_id, run_mode) to the generic pipeline_runs row.
--   2. Every status/rows_*/error/timing field stays on pipeline_runs — we
--      do NOT duplicate those here.
--
-- Design decision (plan R2):
--   sync_jobs owns only the Control Center linkage. When the caller wants
--   sync history, we JOIN sync_jobs → pipeline_runs. This avoids having
--   two sources of truth for run status.

CREATE TABLE IF NOT EXISTS public.sync_jobs (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id            INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    pipeline_run_id      UUID REFERENCES public.pipeline_runs(id) ON DELETE SET NULL,
    source_connection_id BIGINT NOT NULL REFERENCES public.source_connections(id) ON DELETE CASCADE,
    release_id           BIGINT REFERENCES public.pipeline_releases(id) ON DELETE SET NULL,
    profile_id           BIGINT REFERENCES public.pipeline_profiles(id) ON DELETE SET NULL,
    run_mode             VARCHAR(20) NOT NULL DEFAULT 'manual',
    created_by           TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_sync_jobs_run_mode CHECK (run_mode IN ('manual', 'scheduled', 'webhook', 'watcher'))
);

CREATE INDEX IF NOT EXISTS idx_sync_jobs_tenant_created
    ON public.sync_jobs (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sync_jobs_connection
    ON public.sync_jobs (source_connection_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sync_jobs_pipeline_run
    ON public.sync_jobs (pipeline_run_id)
    WHERE pipeline_run_id IS NOT NULL;

ALTER TABLE public.sync_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_jobs FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.sync_jobs
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_write ON public.sync_jobs
        FOR ALL TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.sync_jobs TO datapulse_reader;

COMMENT ON TABLE public.sync_jobs IS
    'Control Center: links a source_connection + release + profile to a '
    'pipeline_runs execution. All status/timing/rows data lives on '
    'pipeline_runs — sync_jobs only holds Control-Center-specific metadata.';
