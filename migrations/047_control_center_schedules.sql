-- Migration: 047 — Control Center: sync_schedules
-- Layer: application / control_center
-- Phase: Control Center Phase 2 (Google Sheets + Scheduled Sync)
--
-- Run order: after 046_control_center_permissions.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS, DO $$ BEGIN...EXCEPTION)
--
-- What this does:
--   1. Creates sync_schedules — cron-based schedule for a source connection.
--      APScheduler loads active rows on startup and registers each as a
--      CronTrigger job calling service.trigger_sync().
--   2. Adds 'control_center:sync:schedule' permission and grants it to
--      owner and admin roles.

-- ============================================================
-- 1. sync_schedules table
-- ============================================================

CREATE TABLE IF NOT EXISTS public.sync_schedules (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    connection_id INT NOT NULL REFERENCES public.source_connections(id) ON DELETE CASCADE,
    cron_expr     VARCHAR(100) NOT NULL,       -- e.g. '0 6 * * *'
    is_active     BOOL NOT NULL DEFAULT true,
    last_run_at   TIMESTAMPTZ,
    created_by    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sync_schedules_active
    ON public.sync_schedules (is_active, connection_id);

CREATE INDEX IF NOT EXISTS idx_sync_schedules_tenant
    ON public.sync_schedules (tenant_id, created_at DESC);

-- ============================================================
-- 2. RLS
-- ============================================================

ALTER TABLE public.sync_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_schedules FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.sync_schedules
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.sync_schedules
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_write ON public.sync_schedules
        FOR ALL TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.sync_schedules TO datapulse_reader;

-- ============================================================
-- 3. New permission: control_center:sync:schedule
-- ============================================================

INSERT INTO public.permissions (permission_key, category, description) VALUES
    ('control_center:sync:schedule', 'control_center', 'Create and delete sync schedules for source connections')
ON CONFLICT (permission_key) DO NOTHING;

-- Grant to owner (all permissions)
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'owner'
  AND p.permission_key = 'control_center:sync:schedule'
ON CONFLICT DO NOTHING;

-- Grant to admin
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'admin'
  AND p.permission_key = 'control_center:sync:schedule'
ON CONFLICT DO NOTHING;

COMMENT ON TABLE public.sync_schedules IS
    'Control Center: cron schedule for auto-triggering sync_jobs on a source '
    'connection. APScheduler loads is_active=true rows on startup and registers '
    'each as a CronTrigger job.';
