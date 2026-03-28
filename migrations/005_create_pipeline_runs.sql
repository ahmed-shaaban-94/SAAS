-- Migration: Create pipeline_runs table for tracking ETL pipeline executions
-- Layer: Application / Pipeline Monitoring
-- Phase: 2.2 (Pipeline Status Tracking)
--
-- Run order: after 004_create_n8n_schema.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- What this does:
--   1. Creates the pipeline_runs table in public schema
--   2. Adds indexes for common query patterns
--   3. Enables tenant-scoped Row Level Security
--   4. Comments the table for documentation

-- ============================================================
-- 1. Create pipeline_runs table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    run_type         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    trigger_source   TEXT,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at      TIMESTAMPTZ,
    duration_seconds NUMERIC(10,2),
    rows_loaded      INT,
    error_message    TEXT,
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- ============================================================
-- 2. Indexes for common query patterns
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_tenant_status
    ON public.pipeline_runs(tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON public.pipeline_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_type
    ON public.pipeline_runs(run_type);

-- ============================================================
-- 3. Row Level Security
-- ============================================================
ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_runs FORCE ROW LEVEL SECURITY;

-- Owner policy: datapulse user has full access
DO $$ BEGIN
    CREATE POLICY owner_all ON public.pipeline_runs
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Reader policy: datapulse_reader scoped by tenant_id session variable
DO $$ BEGIN
    CREATE POLICY reader_select ON public.pipeline_runs
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 4. Table comment
-- ============================================================
COMMENT ON TABLE public.pipeline_runs IS
    'Tracks ETL pipeline execution status with tenant-scoped RLS — Phase 2.2';
