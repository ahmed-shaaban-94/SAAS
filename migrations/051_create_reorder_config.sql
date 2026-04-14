-- Migration: 051 — Reorder configuration table
-- Layer: Application
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.reorder_config (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           INT NOT NULL,
    drug_code           TEXT NOT NULL,
    site_code           TEXT NOT NULL,
    min_stock           NUMERIC(18,4) NOT NULL DEFAULT 0,
    reorder_point       NUMERIC(18,4) NOT NULL DEFAULT 0,
    max_stock           NUMERIC(18,4) NOT NULL DEFAULT 0,
    reorder_lead_days   INT NOT NULL DEFAULT 7,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          TEXT,
    UNIQUE (tenant_id, drug_code, site_code)
);

CREATE INDEX IF NOT EXISTS idx_reorder_config_tenant_drug_site
    ON public.reorder_config(tenant_id, drug_code, site_code, is_active);

ALTER TABLE public.reorder_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reorder_config FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.reorder_config
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.reorder_config
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE public.reorder_config TO datapulse_reader;

COMMENT ON TABLE public.reorder_config IS
    'Per-drug per-site reorder thresholds: min, reorder point, max stock levels. RLS-protected.';
