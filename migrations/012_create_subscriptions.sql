-- Migration: Create subscription & usage tracking tables for Stripe billing
-- Layer: Application / Billing
-- Phase: 5 (Multi-tenancy & Billing)
--
-- Run order: after 011_create_targets.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- What this does:
--   1. Adds stripe_customer_id, plan, plan_limits to bronze.tenants
--   2. Creates public.subscriptions table
--   3. Creates public.usage_metrics table
--   4. Enables tenant-scoped RLS on new tables

-- ============================================================
-- 1. Extend bronze.tenants with billing columns
-- ============================================================
-- Postgres 16+: ADD COLUMN IF NOT EXISTS is the canonical idempotent form.
ALTER TABLE bronze.tenants ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE bronze.tenants ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'starter';
ALTER TABLE bronze.tenants ADD COLUMN IF NOT EXISTS plan_limits JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Unique index on stripe_customer_id (partial — only non-null values)
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_stripe_customer_id
    ON bronze.tenants(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- ============================================================
-- 2. Create subscriptions table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id                      SERIAL PRIMARY KEY,
    tenant_id               INT NOT NULL REFERENCES bronze.tenants(tenant_id),
    stripe_subscription_id  TEXT UNIQUE NOT NULL,
    stripe_price_id         TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'active',
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    cancel_at_period_end    BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant_id
    ON public.subscriptions(tenant_id);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status
    ON public.subscriptions(status);

-- ============================================================
-- 3. Create usage_metrics table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.usage_metrics (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INT NOT NULL UNIQUE REFERENCES bronze.tenants(tenant_id),
    data_sources_count  INT NOT NULL DEFAULT 0,
    total_rows          BIGINT NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 4. Row Level Security — subscriptions
-- ============================================================
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.subscriptions
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.subscriptions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 5. Row Level Security — usage_metrics
-- ============================================================
ALTER TABLE public.usage_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_metrics FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.usage_metrics
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.usage_metrics
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 6. Table comments
-- ============================================================
COMMENT ON TABLE public.subscriptions IS
    'Stripe subscription records linked to tenants — Phase 5 Billing';

COMMENT ON TABLE public.usage_metrics IS
    'Per-tenant usage counters for plan limit enforcement — Phase 5 Billing';
