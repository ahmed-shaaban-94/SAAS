-- Migration: 042 — Control Center: canonical_domains + pipeline_profiles
-- Layer: application / control_center
-- Phase: Control Center Phase 1a (Foundation)
--
-- Run order: after 041_control_center_sources.sql
-- Idempotent: safe to run multiple times
--
-- What this does:
--   1. Creates canonical_domains seed table — single source of truth for
--      "semantic schemas" DataPulse supports (sales_orders, inventory_snapshot,
--      products, customers, sites). JSON schema stored per domain version.
--   2. Seeds the 5 canonical domains with required_fields & type hints.
--   3. Creates pipeline_profiles — tenant-specific processing profiles that
--      FK to canonical_domains.
--
-- Design notes:
--   - canonical_domains is global (no tenant_id) — the semantic layer is
--     shared across all tenants. RLS disabled.
--   - pipeline_profiles.target_domain FKs canonical_domains.domain_key —
--     every profile MUST map to a known semantic domain.

-- ============================================================
-- 1. Canonical domains (global, shared across tenants)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.canonical_domains (
    domain_key   VARCHAR(100) PRIMARY KEY,
    version      INT NOT NULL DEFAULT 1,
    display_name TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    json_schema  JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.canonical_domains IS
    'Global registry of canonical semantic domains. Every Control Center '
    'pipeline_profile maps to one domain. json_schema defines required_fields '
    'and type hints used by the validation engine.';

-- Seed canonical domains (idempotent)
INSERT INTO public.canonical_domains (domain_key, version, display_name, description, json_schema)
VALUES
    ('sales_orders', 1, 'Sales Orders',
     'Transactional sales records',
     '{"required_fields": ["order_id","customer_id","product_id","qty","gross_amount","order_date"],
       "types": {"order_id":"string","customer_id":"string","product_id":"string",
                 "qty":"integer","gross_amount":"numeric","order_date":"date"}}'::jsonb),
    ('inventory_snapshot', 1, 'Inventory Snapshot',
     'Point-in-time stock levels per SKU per warehouse',
     '{"required_fields": ["sku","qty","warehouse","snapshot_date"],
       "types": {"sku":"string","qty":"integer","warehouse":"string","snapshot_date":"date"}}'::jsonb),
    ('products', 1, 'Products',
     'Product master data',
     '{"required_fields": ["product_id","name","category"],
       "types": {"product_id":"string","name":"string","category":"string"}}'::jsonb),
    ('customers', 1, 'Customers',
     'Customer master data',
     '{"required_fields": ["customer_id","name"],
       "types": {"customer_id":"string","name":"string"}}'::jsonb),
    ('sites', 1, 'Sites',
     'Physical locations / stores / warehouses',
     '{"required_fields": ["site_code","name"],
       "types": {"site_code":"string","name":"string"}}'::jsonb)
ON CONFLICT (domain_key) DO NOTHING;

GRANT SELECT ON TABLE public.canonical_domains TO datapulse_reader;

-- ============================================================
-- 2. Pipeline profiles (tenant-scoped)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pipeline_profiles (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id      INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    profile_key    VARCHAR(100) NOT NULL,
    display_name   VARCHAR(200) NOT NULL,
    target_domain  VARCHAR(100) NOT NULL REFERENCES public.canonical_domains(domain_key),
    is_default     BOOLEAN NOT NULL DEFAULT FALSE,
    config_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_pipeline_profiles_tenant_key UNIQUE (tenant_id, profile_key)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_profiles_tenant
    ON public.pipeline_profiles (tenant_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_profiles_domain
    ON public.pipeline_profiles (target_domain);

DROP TRIGGER IF EXISTS trg_pipeline_profiles_updated_at ON public.pipeline_profiles;
CREATE TRIGGER trg_pipeline_profiles_updated_at
    BEFORE UPDATE ON public.pipeline_profiles
    FOR EACH ROW EXECUTE FUNCTION public.control_center_set_updated_at();

ALTER TABLE public.pipeline_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_profiles FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.pipeline_profiles
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_write ON public.pipeline_profiles
        FOR ALL TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.pipeline_profiles TO datapulse_reader;

COMMENT ON TABLE public.pipeline_profiles IS
    'Control Center: tenant-specific pipeline profiles. Each profile targets '
    'one canonical_domain and defines processing rules (quality thresholds, '
    'required fields, key uniqueness) in config_json.';
