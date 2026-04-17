-- Migration: 048 — Control Center: Encrypted credential storage
-- Layer: application / control_center
-- Phase: Control Center Phase 3 (Postgres connector + pgcrypto credentials)
--
-- Run order: after 047_control_center_schedules.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS, ON CONFLICT DO NOTHING)
--
-- What this does:
--   1. Creates public.source_credentials table for encrypted credential storage.
--   2. Encryption is performed with pgcrypto pgp_sym_encrypt/pgp_sym_decrypt.
--   3. The symmetric key is supplied at runtime via the CONTROL_CENTER_CREDS_KEY
--      environment variable (settings.control_center_creds_key).
--   4. Applies RLS matching the existing pattern from migrations 041–046.
--
-- Security notes:
--   - The encrypted_value column MUST NEVER appear in any API response model.
--   - The CONTROL_CENTER_CREDS_KEY env var must be set before any credential
--     operation is attempted — the service layer enforces this at runtime.
--   - To rotate the key: re-encrypt all rows with the new key using the
--     helper script tools/rotate_creds_key.py (to be created in Phase 3b).
--
-- pgcrypto:
--   pgcrypto is enabled by an earlier migration (CREATE EXTENSION IF NOT EXISTS pgcrypto).
--   No need to re-create it here.
--
-- CONTROL_CENTER_CREDS_KEY: add to your .env file as a long random secret:
--   CONTROL_CENTER_CREDS_KEY=<openssl rand -base64 48>

-- ============================================================
-- 1. Create source_credentials table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.source_credentials (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL REFERENCES bronze.tenants(tenant_id),
    connection_id    INT NOT NULL REFERENCES public.source_connections(id) ON DELETE CASCADE,
    credential_type  VARCHAR(50) NOT NULL,  -- 'password' | 'service_account' | 'connection_string'
    encrypted_value  TEXT NOT NULL,         -- pgp_sym_encrypt(plain_value, key) output
    created_by       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_credentials_conn UNIQUE (connection_id, credential_type)
);

-- ============================================================
-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_source_credentials_connection
    ON public.source_credentials (connection_id);

CREATE INDEX IF NOT EXISTS idx_source_credentials_tenant
    ON public.source_credentials (tenant_id);

-- ============================================================
-- 3. Row-Level Security
-- ============================================================
ALTER TABLE public.source_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_credentials FORCE ROW LEVEL SECURITY;

-- Service role: full access (no RLS filter — app.tenant_id enforced via JOIN)
DO $$ BEGIN
    CREATE POLICY owner_all ON public.source_credentials
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Reader role: tenant-scoped SELECT only
DO $$ BEGIN
    CREATE POLICY reader_select ON public.source_credentials
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
