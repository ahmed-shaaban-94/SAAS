-- Migration: 107 — pharma schema, drug_master catalog, and EDA exports
-- Layer: pharma (new schema)
-- Idempotent.
--
-- Creates:
--   1. pharma schema
--   2. pharma.drug_master  — shared drug catalog (no RLS; all tenants read)
--   3. pharma.eda_exports  — per-tenant EDA reporting records (RLS tenant-scoped)

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Schema
-- ─────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS pharma;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. pharma.drug_master
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pharma.drug_master (
    ean13                TEXT          PRIMARY KEY,
    name_en              TEXT          NOT NULL,
    name_ar              TEXT,
    strength             TEXT,
    form                 TEXT,
    atc_code             TEXT,
    controlled_schedule  SMALLINT      NOT NULL DEFAULT 0,
    default_price_egp    NUMERIC(10,2),
    active_ingredient    TEXT,
    is_active            BOOL          NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_drug_master_name_en -- migration-safety: ok
    ON pharma.drug_master (name_en);

CREATE INDEX IF NOT EXISTS idx_drug_master_atc_code -- migration-safety: ok
    ON pharma.drug_master (atc_code)
    WHERE atc_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_drug_master_active_ingredient -- migration-safety: ok
    ON pharma.drug_master (active_ingredient)
    WHERE active_ingredient IS NOT NULL;

COMMENT ON TABLE pharma.drug_master IS
    'Shared drug catalog (EAN-13 keyed). No RLS — all tenants read. '
    'Controlled schedule: 0 = OTC, 1–5 = Egyptian controlled drug schedule. '
    'Added in migration 107.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. pharma.eda_exports
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pharma.eda_exports (
    id           BIGSERIAL     PRIMARY KEY,
    tenant_id    BIGINT        NOT NULL,
    period_start DATE,
    period_end   DATE,
    export_type  TEXT          NOT NULL CHECK (export_type IN ('monthly', 'controlled')),
    file_path    TEXT,
    file_sha256  TEXT,
    row_count    INT,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    created_by   TEXT
);

CREATE INDEX IF NOT EXISTS idx_eda_exports_tenant_id -- migration-safety: ok
    ON pharma.eda_exports (tenant_id);

CREATE INDEX IF NOT EXISTS idx_eda_exports_period -- migration-safety: ok
    ON pharma.eda_exports (tenant_id, period_start, period_end);

COMMENT ON TABLE pharma.eda_exports IS
    'Per-tenant EDA (Egyptian Drug Authority) export records. '
    'Tenant-scoped via RLS. Added in migration 107.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. RLS on pharma.eda_exports (drug_master is shared — no RLS)
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE pharma.eda_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE pharma.eda_exports FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON pharma.eda_exports
        USING (tenant_id = current_setting('app.tenant_id', true)::bigint);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Grants (guarded — role may not exist in all environments)
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_api') THEN
        GRANT SELECT                 ON TABLE pharma.drug_master              TO datapulse_api;
        GRANT SELECT, INSERT, UPDATE ON TABLE pharma.eda_exports              TO datapulse_api;
        GRANT USAGE, SELECT          ON SEQUENCE pharma.eda_exports_id_seq    TO datapulse_api;
    END IF;
END $$;
