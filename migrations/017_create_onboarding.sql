-- Migration: 017 – Onboarding progress tracking
-- Layer: application
--
-- Run order: after 016_*.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)

-- ============================================================
-- 1. Create onboarding table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.onboarding (
    id               SERIAL PRIMARY KEY,
    tenant_id        INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    user_id          TEXT NOT NULL,
    steps_completed  TEXT[] NOT NULL DEFAULT '{}',
    current_step     TEXT NOT NULL DEFAULT 'connect_data',
    completed_at     TIMESTAMPTZ,
    skipped_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
);

-- ============================================================
-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_onboarding_tenant_user
    ON public.onboarding(tenant_id, user_id);

-- ============================================================
-- 3. Row Level Security
-- ============================================================
ALTER TABLE public.onboarding ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.onboarding FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.onboarding
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.onboarding
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TABLE public.onboarding IS 'Onboarding wizard progress tracking per user/tenant';
