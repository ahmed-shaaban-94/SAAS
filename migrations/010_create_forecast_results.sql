-- Migration: Create forecast_results table for storing forecasting output
-- Layer: Application / Forecasting
-- Phase: Feature Store + Forecasting
--
-- Run order: after 009_create_performance_indexes.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- What this does:
--   1. Creates the forecast_results table in public schema
--   2. Adds indexes for common query patterns
--   3. Enables tenant-scoped Row Level Security
--   4. Comments the table for documentation

-- ============================================================
-- 1. Create forecast_results table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.forecast_results (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    entity_type      TEXT NOT NULL,          -- 'revenue', 'product'
    entity_key       INT,                    -- NULL for revenue, product_key for product
    granularity      TEXT NOT NULL,          -- 'daily', 'monthly'
    method           TEXT NOT NULL,          -- 'holt_winters', 'sma', 'seasonal_naive'
    forecast_date    DATE NOT NULL,          -- the date being predicted
    point_forecast   NUMERIC(18,2) NOT NULL,
    lower_bound      NUMERIC(18,2),
    upper_bound      NUMERIC(18,2),
    mape             NUMERIC(8,4),           -- Mean Absolute Percentage Error
    mae              NUMERIC(18,2),          -- Mean Absolute Error
    rmse             NUMERIC(18,2),          -- Root Mean Squared Error
    run_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, entity_type, entity_key, granularity, forecast_date)
);

-- ============================================================
-- 2. Indexes for common query patterns
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_forecast_results_lookup
    ON public.forecast_results (tenant_id, entity_type, entity_key, granularity);

CREATE INDEX IF NOT EXISTS idx_forecast_results_run_at
    ON public.forecast_results (run_at DESC);

-- ============================================================
-- 3. Row Level Security
-- ============================================================
ALTER TABLE public.forecast_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forecast_results FORCE ROW LEVEL SECURITY;

-- Owner policy: datapulse user has full access
DO $$ BEGIN
    CREATE POLICY owner_all ON public.forecast_results
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Reader policy: datapulse_reader scoped by tenant_id session variable
DO $$ BEGIN
    CREATE POLICY reader_select ON public.forecast_results
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 4. Table comment
-- ============================================================
COMMENT ON TABLE public.forecast_results IS
    'Stores forecasting output (revenue, product demand) with tenant-scoped RLS — Feature Store + Forecasting phase';
