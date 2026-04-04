-- Migration 014: Add tenant_id and user_id to audit_log for multi-tenant tracking
-- Phase: Session 8 audit — Multi-Tenancy (Phase 13)
--
-- Without these columns, audit logs cannot be filtered per tenant,
-- and there is no record of WHICH user performed an action.

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('014_add_audit_log_tenant_user.sql')
ON CONFLICT (filename) DO NOTHING;

-- 1. Add tenant_id with default 1 (backfills existing rows)
ALTER TABLE public.audit_log
    ADD COLUMN IF NOT EXISTS tenant_id INT NOT NULL DEFAULT 1
    REFERENCES bronze.tenants(tenant_id);

-- 2. Add user_id (nullable — some actions may be unauthenticated)
ALTER TABLE public.audit_log
    ADD COLUMN IF NOT EXISTS user_id TEXT;

-- 3. Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_id
    ON public.audit_log (tenant_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id
    ON public.audit_log (user_id)
    WHERE user_id IS NOT NULL;

-- 4. Enable RLS (was missing on audit_log)
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.audit_log
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.audit_log
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TABLE public.audit_log IS
    'API request audit trail with tenant + user tracking — Phase 13 Multi-Tenancy';

COMMIT;
