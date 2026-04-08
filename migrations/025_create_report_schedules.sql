-- Migration 025: Create report_schedules table for scheduled PDF reports
-- Stores cron-based report schedules with recipients and parameters

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('025_create_report_schedules.sql')
ON CONFLICT (filename) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.report_schedules (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    name TEXT NOT NULL,
    report_type TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    recipients JSONB NOT NULL DEFAULT '[]',
    parameters JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_schedules_tenant
    ON public.report_schedules (tenant_id);
CREATE INDEX IF NOT EXISTS idx_report_schedules_enabled
    ON public.report_schedules (enabled) WHERE enabled = TRUE;

-- RLS
ALTER TABLE public.report_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_schedules FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.report_schedules
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.report_schedules
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
