-- Migration: 041 — Control Center: source_connections
-- Layer: application / control_center
-- Phase: Control Center Phase 1a (Foundation)
--
-- Run order: after 040_brain_knowledge.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- What this does:
--   1. Creates source_connections table in public schema
--   2. Adds indexes for tenant lookups + sync status
--   3. Enables tenant-scoped Row Level Security
--
-- Design notes:
--   - BIGINT IDENTITY PK (not UUID) — entities never leave the system boundary
--   - tenant_id INT FK to bronze.tenants (matches all existing DataPulse tables)
--   - credentials_ref is nullable & indirect — creds live in a future
--     source_credentials table with pgcrypto (Phase 3). Never store secrets
--     in config_json.
--   - source_type is open-ended TEXT (not ENUM) to allow new connectors
--     (Phase 1: 'file_upload'; Phase 2: 'google_sheets'; Phase 3: 'postgres').

-- ============================================================
-- 1. Create source_connections table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.source_connections (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    source_type     VARCHAR(50) NOT NULL,  -- 'file_upload' | 'google_sheets' | 'postgres' | ...
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    config_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    credentials_ref VARCHAR(255),          -- nullable; points to external secret (Phase 3)
    last_sync_at    TIMESTAMPTZ,
    created_by      TEXT,                  -- auth0 sub
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_connections_tenant_name UNIQUE (tenant_id, name),
    CONSTRAINT chk_source_connections_status
        CHECK (status IN ('draft', 'active', 'error', 'archived'))
);

-- ============================================================
-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_source_connections_tenant
    ON public.source_connections (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_source_connections_type
    ON public.source_connections (tenant_id, source_type);

-- ============================================================
-- 3. updated_at trigger (reuses helper if present, else inline)
-- ============================================================
CREATE OR REPLACE FUNCTION public.control_center_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_source_connections_updated_at ON public.source_connections;
CREATE TRIGGER trg_source_connections_updated_at
    BEFORE UPDATE ON public.source_connections
    FOR EACH ROW EXECUTE FUNCTION public.control_center_set_updated_at();

-- ============================================================
-- 4. Row Level Security
-- ============================================================
ALTER TABLE public.source_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_connections FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.source_connections
        FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.source_connections
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_write ON public.source_connections
        FOR ALL TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.source_connections TO datapulse_reader;

-- ============================================================
-- 5. Table comment
-- ============================================================
COMMENT ON TABLE public.source_connections IS
    'Control Center: registered data sources per tenant. Phase 1 supports '
    'source_type=file_upload only. config_json holds source-specific settings '
    '(never credentials — those live in source_credentials with pgcrypto).';
