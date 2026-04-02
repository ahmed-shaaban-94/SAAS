-- Migration: Create sales_targets table for budget/target tracking
-- Layer: Application / Goals & Targets
-- Phase: CEO Review
--
-- Run order: after 010_create_forecast_results.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)

-- ============================================================
-- 1. Create sales_targets table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.sales_targets (
    id               SERIAL PRIMARY KEY,
    tenant_id        INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    target_type      TEXT NOT NULL,          -- 'revenue', 'transactions', 'customers'
    granularity      TEXT NOT NULL,          -- 'daily', 'monthly', 'yearly'
    period           TEXT NOT NULL,          -- '2026-04', '2026-04-01', '2026'
    target_value     NUMERIC(18,4) NOT NULL,
    entity_type      TEXT,                   -- NULL=overall, 'site', 'staff', 'product'
    entity_key       INT,                    -- FK to relevant dimension
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, target_type, granularity, period, entity_type, entity_key)
);

-- ============================================================
-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_targets_tenant_period
    ON public.sales_targets(tenant_id, period);

CREATE INDEX IF NOT EXISTS idx_targets_type_granularity
    ON public.sales_targets(target_type, granularity);

-- ============================================================
-- 3. Row Level Security
-- ============================================================
ALTER TABLE public.sales_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_targets FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.sales_targets
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.sales_targets
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 4. Create alerts_config table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.alerts_config (
    id               SERIAL PRIMARY KEY,
    tenant_id        INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    alert_name       TEXT NOT NULL,
    metric           TEXT NOT NULL,          -- 'daily_revenue', 'return_rate', 'transactions'
    condition        TEXT NOT NULL,          -- 'below', 'above', 'change_pct'
    threshold        NUMERIC(18,4) NOT NULL,
    entity_type      TEXT,                   -- NULL=overall, 'site', 'product'
    entity_key       INT,
    enabled          BOOLEAN NOT NULL DEFAULT true,
    notify_channels  JSONB NOT NULL DEFAULT '["dashboard"]'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.alerts_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts_config FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.alerts_config
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.alerts_config
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 5. Create alerts_log table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.alerts_log (
    id               SERIAL PRIMARY KEY,
    tenant_id        INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    alert_config_id  INT REFERENCES public.alerts_config(id),
    fired_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    metric_value     NUMERIC(18,4),
    threshold_value  NUMERIC(18,4),
    message          TEXT,
    acknowledged     BOOLEAN NOT NULL DEFAULT false,
    acknowledged_at  TIMESTAMPTZ
);

ALTER TABLE public.alerts_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts_log FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.alerts_log
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.alerts_log
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TABLE public.sales_targets IS 'Budget/target tracking per entity/period — CEO Review';
COMMENT ON TABLE public.alerts_config IS 'Configurable metric alerts — CEO Review';
COMMENT ON TABLE public.alerts_log IS 'Alert firing history — CEO Review';
