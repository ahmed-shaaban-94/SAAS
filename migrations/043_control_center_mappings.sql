-- Migration: 043 — Control Center: mapping_templates
-- Layer: application / control_center
-- Phase: Control Center Phase 1a (Foundation)
--
-- Run order: after 042_control_center_profiles.sql
-- Idempotent: safe to run multiple times
--
-- What this does:
--   1. Creates mapping_templates — the column-rename / type-cast rules that
--      turn a source's raw schema into a canonical domain's schema.
--   2. Stores mapping_json as JSONB (source_column -> canonical_field + cast).
--   3. source_schema_hash lets us reuse templates when the same CSV shape
--      appears in multiple tenants or multiple connections.

CREATE TABLE IF NOT EXISTS public.mapping_templates (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id          INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    source_type        VARCHAR(50) NOT NULL,
    template_name      VARCHAR(200) NOT NULL,
    source_schema_hash VARCHAR(128),
    mapping_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    version            INT NOT NULL DEFAULT 1,
    created_by         TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_mapping_templates_tenant_name_version
        UNIQUE (tenant_id, template_name, version)
);

CREATE INDEX IF NOT EXISTS idx_mapping_templates_tenant
    ON public.mapping_templates (tenant_id, source_type);

CREATE INDEX IF NOT EXISTS idx_mapping_templates_schema_hash
    ON public.mapping_templates (source_schema_hash)
    WHERE source_schema_hash IS NOT NULL;

DROP TRIGGER IF EXISTS trg_mapping_templates_updated_at ON public.mapping_templates;
CREATE TRIGGER trg_mapping_templates_updated_at
    BEFORE UPDATE ON public.mapping_templates
    FOR EACH ROW EXECUTE FUNCTION public.control_center_set_updated_at();

ALTER TABLE public.mapping_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mapping_templates FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.mapping_templates
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_write ON public.mapping_templates
        FOR ALL TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.mapping_templates TO datapulse_reader;

COMMENT ON TABLE public.mapping_templates IS
    'Control Center: column-mapping templates that transform a source schema '
    'into a canonical domain schema. mapping_json shape: '
    '{"columns": [{"source":"col_a","canonical":"field_x","cast":"integer"}, ...]}';
