-- Migration: 030 – Fix RLS cast pattern and add missing tenant FK constraints
-- Layer: Security / Multi-tenancy
-- Fixes: H1.8 (wrong RLS cast pattern) + H1.9 (missing FK to bronze.tenants)
--
-- Run order: after 029_seed_initial_members.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- Affected tables (all in public schema):
--   public.saved_views        (migration 019)
--   public.notifications      (migration 020)
--   public.dashboard_layouts  (migration 021)
--   public.annotations        (migration 022)
--
-- H1.8 – Wrong RLS cast pattern:
--   OLD (broken): tenant_id::text = current_setting('app.tenant_id', true)
--     Risk: empty string '' compares as false (not NULL) — inconsistent fail-closed behaviour.
--   NEW (canonical): tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT
--     NULLIF returns NULL when app.tenant_id is unset → NULL = N is NULL (fail-closed).
--
-- H1.9 – Missing FK:
--   tenant_id INT NOT NULL had no REFERENCES bronze.tenants(tenant_id).
--   Every other user-facing table has this FK. Added via DO $$ guard for idempotency.

-- ============================================================
-- public.saved_views
-- ============================================================

-- H1.9: Add FK constraint (idempotent — checks pg_constraint first)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'saved_views_tenant_id_fkey'
          AND conrelid = 'public.saved_views'::regclass
    ) THEN
        ALTER TABLE public.saved_views
            ADD CONSTRAINT saved_views_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id);
    END IF;
END $$;

-- H1.8: Replace RLS policy with correct NULLIF cast
DROP POLICY IF EXISTS tenant_isolation_saved_views ON public.saved_views;
CREATE POLICY tenant_isolation_saved_views ON public.saved_views
    FOR ALL TO datapulse_reader
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);

-- ============================================================
-- public.notifications
-- ============================================================

-- H1.9: Add FK constraint (idempotent)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'notifications_tenant_id_fkey'
          AND conrelid = 'public.notifications'::regclass
    ) THEN
        ALTER TABLE public.notifications
            ADD CONSTRAINT notifications_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id);
    END IF;
END $$;

-- H1.8: Replace RLS policy with correct NULLIF cast
DROP POLICY IF EXISTS tenant_isolation_notifications ON public.notifications;
CREATE POLICY tenant_isolation_notifications ON public.notifications
    FOR ALL TO datapulse_reader
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);

-- ============================================================
-- public.dashboard_layouts
-- ============================================================

-- H1.9: Add FK constraint (idempotent)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'dashboard_layouts_tenant_id_fkey'
          AND conrelid = 'public.dashboard_layouts'::regclass
    ) THEN
        ALTER TABLE public.dashboard_layouts
            ADD CONSTRAINT dashboard_layouts_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id);
    END IF;
END $$;

-- H1.8: Replace RLS policy with correct NULLIF cast
DROP POLICY IF EXISTS tenant_isolation_dashboard_layouts ON public.dashboard_layouts;
CREATE POLICY tenant_isolation_dashboard_layouts ON public.dashboard_layouts
    FOR ALL TO datapulse_reader
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);

-- ============================================================
-- public.annotations
-- ============================================================

-- H1.9: Add FK constraint (idempotent)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'annotations_tenant_id_fkey'
          AND conrelid = 'public.annotations'::regclass
    ) THEN
        ALTER TABLE public.annotations
            ADD CONSTRAINT annotations_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id);
    END IF;
END $$;

-- H1.8: Replace RLS policy with correct NULLIF cast
DROP POLICY IF EXISTS tenant_isolation_annotations ON public.annotations;
CREATE POLICY tenant_isolation_annotations ON public.annotations
    FOR ALL TO datapulse_reader
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
